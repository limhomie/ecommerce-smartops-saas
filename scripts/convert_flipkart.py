"""Convert Flipkart dataset to knowledge base documents."""

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


def main() -> int:
    with open(SRC, encoding="utf-8") as f:
        products = json.load(f)

    OUT.mkdir(parents=True, exist_ok=True)

    # Clear old generated files
    for old in OUT.glob("prod_*.md"):
        old.unlink()

    count = 0
    for i, p in enumerate(products):
        if i >= MAX_PRODUCTS:
            break
        content = (
            f"# {p.get('product_name', 'Product')}\n\n"
            f"- Price: INR {p.get('selling_price', 'N/A')}\n"
            f"- Brand: {p.get('brand_name', 'N/A')}\n"
            f"- Category: {p.get('product_category_tree', 'N/A')}\n"
            f"- Description: {p.get('description', 'N/A')}\n"
            f"- Rating: {p.get('product_rating', 'N/A')}\n"
        )
        (OUT / f"prod_{i:06d}.md").write_text(content, encoding="utf-8")
        count += 1

    print(f"Converted {count} products to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
