"""Classes to help with dataset preparation."""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


class Image:
    def __init__(self, path: Union[Path, str], subfolders: Optional[List[str]] = None):
        self.path = path if isinstance(path, Path) else Path(path)
        self.subfolders = subfolders if subfolders else []
        self._metadata: Optional[Dict[str, Any]] = None

    @property
    def metadata(self) -> Dict[str, Any]:
        if self._metadata is None:
            self._metadata = self.load_metadata()
        return self._metadata

    @property
    def tags(self):
        if "tags" not in self.metadata:
            self.metadata["tags"] = []
        return self.metadata.get("tags", [])

    @tags.setter
    def tags(self, tags: list):
        if "tags" not in self.metadata:
            self.metadata["tags"] = []
        self.metadata["tags"] = tags

    def add_tag(self, tag: str):
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str):
        if tag in self.tags:
            self.tags.remove(tag)

    @property
    def metadata_path(self) -> Path:
        return self.path.parent / (self.path.name + ".json")

    def load_metadata(self) -> Dict[str, Any]:
        with open(self.metadata_path, "r") as f:
            return json.load(f)

    def save_metadata(self):
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)


class DatasetDirectory:
    def __init__(self, path: str):
        self.path = path
        self.images = self.get_images()

    def get_images(self) -> List[Image]:
        """Fetches all images in the dataset directory recursively."""
        images = []
        for root, _, files in os.walk(self.path):
            for file in files:
                if not file.endswith((".jpg", ".jpeg", ".png", ".webp")):
                    continue
                subfolders = list(Path(root).relative_to(self.path).parts)
                images.append(Image(Path(root) / file, subfolders))
        return images

    def __getitem__(self, index: int) -> Image:
        return self.images[index]

    def __setitem__(self, index: int, image: Image):
        self.images[index] = image

    def __len__(self) -> int:
        return len(self.images)

    def __iter__(self):
        return iter(self.images)
