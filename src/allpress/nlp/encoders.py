import os

import torch
from torch.utils.data import DataLoader, TensorDataset
from sentence_transformers import SentenceTransformer as Model

from allpress.settings import CLASSIFICATION_MODELS_PATH

embedder = Model('paraphrase-multilingual-MiniLM-L12-v2')
class AutoEncoder(torch.nn.Module):
    def __init__(self, input_dim=384, latent_dim=32):
        super().__init__()

        self.encoder = torch.nn.Sequential(
            torch.nn.Linear(input_dim, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, latent_dim),  # Latent space
            torch.nn.Tanh()
        )

        self.decoder = torch.nn.Sequential(
            torch.nn.Linear(latent_dim, 128),
            torch.nn.ReLU(),
            torch.nn.Linear(128, 256),
            torch.nn.ReLU(),
            torch.nn.Linear(256, input_dim)  # Reconstruct back to 384-dim
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))

    def encode(self, x):
        return self.encoder(x)


def train_autoencoder(data_tensor, latent_dim=32, epochs=20, lr=1e-3, batch_size=32):
    input_dim = data_tensor.shape[1]
    model = AutoEncoder(input_dim=input_dim, latent_dim=latent_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = torch.nn.MSELoss()

    # Wrap in DataLoader
    dataset = TensorDataset(data_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0

        for batch in dataloader:
            inputs = batch[0]  # TensorDataset returns tuples
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = loss_fn(outputs, inputs)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * inputs.size(0)  # accumulate per-example loss

        avg_loss = total_loss / len(dataset)
        print(f"Epoch {epoch+1}/{epochs}, Avg Loss: {avg_loss:.6f}", end='\r')

    print("\nTraining complete.")
    return model


def train_semantic_autoencoder(data, latent_dim=32, epochs=50, lr=1e-3):
    """
    Train an autoencoder using semantic embeddings.

    Args:
        data (list of str): List of sentences to encode.
        latent_dim (int): Dimension of the latent space.
        epochs (int): Number of training epochs.
        lr (float): Learning rate for the optimizer.

    Returns:
        AutoEncoder: Trained autoencoder model.
    """
    # Convert sentences to embeddings
    path = os.path.join(CLASSIFICATION_MODELS_PATH, 'semantic_model.pth')
    if os.path.exists(path):
        semantic_model = torch.load(path)
        print("Loaded existing semantic model from disk.")

    else:
        embeddings = embedder.encode(data)
        data_tensor = torch.tensor(embeddings, dtype=torch.float32)
        semantic_model = train_autoencoder(data_tensor, latent_dim, epochs, lr)
        torch.save(semantic_model, path)

    return semantic_model


def train_rhetorical_autoencoder(data, latent_dim=32, epochs=50, lr=1e-3):
    """
    Train an autoencoder using rhetorical embeddings.

    Args:
        data (list of str): List of sentences to encode.
        latent_dim (int): Dimension of the latent space.
        epochs (int): Number of training epochs.
        lr (float): Learning rate for the optimizer.

    Returns:
        AutoEncoder: Trained autoencoder model.
    """
    # Convert sentences to embeddings
    path = os.path.join(CLASSIFICATION_MODELS_PATH, 'rhetoric_model.pth')
    if os.path.exists(path):
        rhetoric_model = torch.load(path)
        print("Loaded existing rhetoric model from disk.")

    else:
        embeddings = embedder.encode(data)
        data_tensor = torch.tensor(embeddings, dtype=torch.float32)
        rhetoric_model = train_autoencoder(data_tensor, latent_dim, epochs, lr)
        torch.save(rhetoric_model, path)

    return rhetoric_model
