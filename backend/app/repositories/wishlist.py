from __future__ import annotations

from app.models.wishlist import WishlistItem
from app.repositories.base import Repository


class WishlistRepository(Repository[WishlistItem]):
    collection_name = "wishlist_items"
    model = WishlistItem
