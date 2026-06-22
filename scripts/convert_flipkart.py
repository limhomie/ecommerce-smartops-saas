"""Convert Flipkart dataset to knowledge base documents.

Generates merged files: N products per file (default 50) to reduce
ChromaDB embedding calls.  5000 products → 100 files.
"""

import json
import os
import sys
from pathlib import Path

SRC = Path(
    os.environ.get("FLIPKART_SRC",
                    str(Path.home() / ".cache/kagglehub/datasets/aaditshukla/"
                        "flipkart-fasion-products-dataset/versions/3/"
                        "flipkart_fashion_products_dataset.json")))
OUT = Path(os.environ.get("FLIPKART_OUT", "data/documents/products"))
MAX_PRODUCTS = int(os.environ.get("PRODUCT_COUNT", "5000"))
PER_FILE = 50  # products per merged file


def main() -> int:
    with open(SRC, encoding="utf-8") as f:
        products = json.load(f)

    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.glob("prod_*.md"):
        old.unlink()

    # Batch into merged files
    file_count = 0
    for batch_start in range(0, min(len(products), MAX_PRODUCTS), PER_FILE):
        batch = products[batch_start:batch_start + PER_FILE]
        lines: list[str] = []
        for i, p in enumerate(batch):
            lines.append(f"## {p.get('product_name', 'Product')}\n")
            lines.append(f"- Price: INR {p.get('selling_price', 'N/A')}\n")
            lines.append(f"- Brand: {p.get('brand_name', 'N/A')}\n")
            lines.append(f"- Category: {p.get('product_category_tree', 'N/A')}\n")
            lines.append(f"- Description: {p.get('description', 'N/A')}\n")
            lines.append(f"- Rating: {p.get('product_rating', 'N/A')}\n")
        fname = f"batch_{batch_start // PER_FILE:04d}.md"
        (OUT / fname).write_text("".join(lines), encoding="utf-8")
        file_count += 1

    print(f"Converted {file_count} files ({PER_FILE} products each) to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
