import os

import torch
import pickle
from torch.utils.data import DataLoader, TensorDataset
from sentence_transformers import SentenceTransformer as Model
from io import BytesIO as IO

from allpress.settings import CLASSIFICATION_MODELS_PATH
from allpress.db.io import connection, cursor

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


def load_vectors_in_batches(column_name, batch_size=10):
    """
    Generator that yields tensors from the specified column in the `page` table.
    """
    query = f"SELECT {column_name} FROM page WHERE {column_name} IS NOT NULL;"
    cursor.execute(query)

    while True:
        rows = cursor.fetchmany(batch_size)
        if not rows:
            break

        for i, row in enumerate(rows):
            blob = row[0]

            if not isinstance(blob, bytes):
                yield str(blob)
            else:
                yield torch.load(IO(blob))


def train_autoencoder_from_db(column_name, model_filename, latent_dim=32, epochs=50, lr=1e-3):
    """
    Train and save autoencoder from database-stored embeddings.
    """
    path = os.path.join(CLASSIFICATION_MODELS_PATH, model_filename)
    if os.path.exists(path):
        print(f"Loaded existing model: {model_filename}")
        return torch.load(path)

    print(f"Training new autoencoder for {column_name}...")
    cursor.execute('SELECT COUNT(*) FROM page;')
    row_count = int(cursor.fetchone()[0])
    data_tensor = torch.empty((row_count, 768 if column_name == 'sem_vec' else 384), dtype=torch.float32)  # Assuming 384-dim vectors

    for i, vector in enumerate(load_vectors_in_batches(column_name)):
        data_tensor[i] = torch.tensor(vector, dtype=torch.float32).squeeze(0)

    model = train_autoencoder(data_tensor, latent_dim, epochs, lr)
    torch.save(model, path)
    return model


def train_semantic_autoencoder(latent_dim=128, epochs=50, lr=1e-3):
    return train_autoencoder_from_db('sem_vec', 'semantic_model.pth', latent_dim, epochs, lr)


def train_rhetorical_autoencoder(latent_dim=32, epochs=50, lr=1e-3):
    return train_autoencoder_from_db('rhet_vec', 'rhetoric_model.pth', latent_dim, epochs, lr)
