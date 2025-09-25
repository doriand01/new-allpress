import torch
import torch_directml
from torch.utils.data import DataLoader, TensorDataset

device = torch.device('cpu')

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


def train_autoencoder(
        training_tensor: torch.Tensor,
        latent_dim: int=256,
        epochs: int=50,
        learning_rate: float=1e-3,
        batch_size: int=2048):
    training_tensor = training_tensor.float()
    input_dim = training_tensor.shape[1]
    model = AutoEncoder(input_dim=input_dim, latent_dim=latent_dim).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = torch.nn.MSELoss()

    # Wrap in DataLoader
    dataset = TensorDataset(training_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=4, pin_memory=False)

    for epoch in range(epochs):
        model.train()
        total_loss = 0.0

        for i, batch in enumerate(dataloader):
            if i > 10:
                break
            inputs = batch[0].to(device)  # TensorDataset returns tuples
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

