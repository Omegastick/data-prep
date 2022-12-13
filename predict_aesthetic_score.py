#!/usr/bin/env python
"""
CLI utility that uses a CLIP-based model to predict aesthetic scores for an image dataset.

Based on https://github.com/christophschuhmann/improved-aesthetic-predictor
"""


import clip
import pytorch_lightning as pl
import torch
import torch.nn as nn
import torch.utils.model_zoo
import tqdm
import typer
from clip.clip import Compose
from clip.model import CLIP
from PIL import Image as PILImage
from PIL import UnidentifiedImageError

from dataset import DatasetDirectory, Image


class MLP(pl.LightningModule):
    def __init__(self, input_size, xcol="emb", ycol="avg_rating"):
        super().__init__()
        self.input_size = input_size
        self.xcol = xcol
        self.ycol = ycol
        self.layers = nn.Sequential(
            nn.Linear(self.input_size, 1024),
            # nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(1024, 128),
            # nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            # nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 16),
            # nn.ReLU(),
            nn.Linear(16, 1),
        )

    def forward(self, x):
        return self.layers(x)

    def training_step(self, batch, batch_idx):
        x = batch[self.xcol]
        y = batch[self.ycol].reshape(-1, 1)
        x_hat = self.layers(x)
        loss = nn.functional.mse_loss(x_hat, y)
        return loss

    def validation_step(self, batch, batch_idx):
        x = batch[self.xcol]
        y = batch[self.ycol].reshape(-1, 1)
        x_hat = self.layers(x)
        loss = nn.functional.mse_loss(x_hat, y)
        return loss

    def configure_optimizers(self):
        optimizer = torch.optim.Adam(self.parameters(), lr=1e-3)
        return optimizer


def normalized(a, axis=-1, order=2):
    import numpy as np  # pylint: disable=import-outside-toplevel

    l2 = np.atleast_1d(np.linalg.norm(a, order, axis))
    l2[l2 == 0] = 1
    return a / np.expand_dims(l2, axis)


def load_clip(device: torch.device) -> tuple[CLIP, Compose]:
    return clip.load("ViT-L/14", device=device)


def load_mlp(device: torch.device) -> MLP:
    state_dict = torch.utils.model_zoo.load_url(
        "https://github.com/christophschuhmann/improved-aesthetic-predictor/raw/main/ava%2Blogos-l14-linearMSE.pth"
    )
    mlp = MLP(768)
    mlp.load_state_dict(state_dict)
    mlp.eval()
    mlp.to(device)

    return mlp


def get_aesthetic_score(image: Image, clip: CLIP, mlp: MLP, preprocess: Compose, device: torch.device) -> float:
    pil_image = PILImage.open(image.path).convert("RGB")
    preprocessed_image = preprocess(pil_image).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = clip.encode_image(preprocessed_image)

    processed_features = normalized(image_features.cpu().detach().numpy())
    prediction = mlp(torch.from_numpy(processed_features).to(device).type(torch.cuda.FloatTensor))

    return prediction.item()


app = typer.Typer()


@app.command()
def predict_aesthetic_scores(
    data_dir: str = typer.Argument(..., help="Path to the data directory"),
    skip_existing: bool = typer.Option(False, help="Skip images that already have an aesthetic score"),
    tag_quality: bool = typer.Option(True, help="Tag images with a quality score"),
) -> None:
    """
    Predict aesthetic scores for images in a directory.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    dataset = DatasetDirectory(data_dir)
    clip_model, preprocess = load_clip(device)
    mlp = load_mlp(device)

    for image in tqdm.tqdm(dataset):
        if skip_existing and "aesthetic_score" in image.metadata:
            typer.echo(f"{image.path}: already has aesthetic score, skipping")
            continue
        try:
            score = get_aesthetic_score(image, clip_model, mlp, preprocess, device)
        except UnidentifiedImageError:
            typer.echo(f"{image.path}: UnidentifiedImageError")
            continue
        typer.echo(f"{image.path}: {score}")
        image.metadata["aesthetic_score"] = score

        if tag_quality:
            if score > 6.5:
                image.add_tag("masterpiece")
            elif score > 6:
                image.add_tag("high quality")
            elif score < 4.5:
                image.add_tag("low quality")

        image.save_metadata()


if __name__ == "__main__":
    app()
