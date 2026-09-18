"""
Agent er TOOL layer.
=====================
Golden rule:
  1. Tool er `description` = LLM er jonno documentation. Eta jotoi valo hobe,
     agent totoi kom vul tool call korbe.
  2. Protita argument er description dite hobe (LLM ei description dekhei
     argument fill kore).
  3. Tool kokhono exception throw korbe na -- error keo string hisebe return
     korbe, jate agent nije recover korte pare.
  4. Return value chhoto + structured rakhte hobe (token khoroch kome).
"""

import json
from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.api_client import APIError, api


# --------------------------------------------------------------------------
# Helper: API response -> LLM-friendly compact string
# --------------------------------------------------------------------------
def _ok(data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(e: APIError) -> str:
    return _ok({"error": True, "status": e.status_code, "message": e.message})


def _slim_product(p: dict) -> dict:
    """LLM ke pura object pathano dorkar nei -- token bachai."""
    return {
        "id": p["id"],
        "name": p["name"],
        "price": p["price"],
        "currency": p["currency"],
        "rating": p["rating"],
        "in_stock": p["stock"] > 0,
        "brand": p["brand"],
        "category": p["category"],
    }


# ==========================================================================
# 1. PRODUCT DISCOVERY
# ==========================================================================
class SearchProductsInput(BaseModel):
    query: Optional[str] = Field(None, description="Free-text keywords, e.g., 'noise cancelling headphone', 'jamdani saree'. Translate Bangla queries to English keywords.")
    category: Optional[str] = Field(None, description="One of: electronics, fashion, home, grocery")
    brand: Optional[str] = Field(None, description="Brand name filter, e.g., 'Aura', 'Nova'")
    min_price: Optional[float] = Field(None, description="Minimum price in BDT")
    max_price: Optional[float] = Field(None, description="Maximum price / customer budget in BDT")
    in_stock_only: bool = Field(False, description="If True, only returns items currently in stock")
    sort_by: str = Field("relevance", description="relevance | price_asc | price_desc | rating")
    limit: int = Field(5, description="Number of results required, default is 5")


@tool("search_products", args_schema=SearchProductsInput)
def search_products(
    query: Optional[str] = None,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    in_stock_only: bool = False,
    sort_by: str = "relevance",
    limit: int = 5,
) -> str:
    """Searches for products in the catalog. Use this tool when a customer wants to buy an item,
    filter by price/budget/brand/category, or asks 'show me what you have'.
    If specific details for a single product are needed, use `get_product_details` instead."""
    try:
        data = api.search_products(
            query=query, category=category, brand=brand, min_price=min_price,
            max_price=max_price, in_stock_only=in_stock_only, sort_by=sort_by, limit=limit,
        )
        return _ok({"count": data["count"], "results": [_slim_product(p) for p in data["results"]]})
    except APIError as e:
        return _err(e)


class ProductIdInput(BaseModel):
    product_id: str = Field(..., description="Product ID, e.g. 'P1001'")


@tool("get_product_details", args_schema=ProductIdInput)
def get_product_details(product_id: str) -> str:
    """Fetches full details for a specific product (description, tags, stock, rating, review count).
    Use this when a customer asks questions like 'tell me more about this', 'what are the specs', or 'how are the reviews?'"""
    try:
        return _ok(api.get_product(product_id))
    except APIError as e:
        return _err(e)


@tool("check_stock", args_schema=ProductIdInput)
def check_stock(product_id: str) -> str:
    """Checks whether a product is in stock and retrieves the available quantity.
    Use this for queries like 'is it in stock?', 'is it available?', or 'when will it be back?'"""
    try:
        return _ok(api.check_stock(product_id))
    except APIError as e:
        return _err(e)


# ==========================================================================
# 2. ORDER TRACKING
# ==========================================================================
class OrderIdInput(BaseModel):
    order_id: str = Field(..., description="Order ID in the format 'ORD-1001'")


@tool("track_order", args_schema=OrderIdInput)
def track_order(order_id: str) -> str:
    """Fetches current status, courier, tracking number, expected delivery date, and full timeline for an order.
    Call this tool when the customer provides an order ID.
    If no order ID is provided, ask the customer for it first or use `list_my_orders`."""
    try:
        o = api.get_order(order_id)
        return _ok({
            "order_id": o["order_id"],
            "status": o["status"],
            "placed_on": o["placed_on"],
            "expected_delivery": o.get("expected_delivery"),
            "delivered_on": o.get("delivered_on"),
            "courier": o.get("courier"),
            "tracking_number": o.get("tracking_number"),
            "items": [{"product_id": i["product_id"], "name": i["name"], "qty": i["qty"]} for i in o["items"]],
            "total": o["total"],
            "currency": o["currency"],
            "timeline": o["timeline"],
        })
    except APIError as e:
        return _err(e)


class UserOrdersInput(BaseModel):
    user_id: str = Field(..., description="Logged-in user ID, e.g., 'U100'")
    limit: int = Field(5, description="Number of recent orders required")


@tool("list_my_orders", args_schema=UserOrdersInput)
def list_my_orders(user_id: str, limit: int = 5) -> str:
    """Retrieves a list of recent orders for a customer. Use this tool when the customer cannot
    remember their order ID (e.g., 'what is the status of my last order?'), then call `track_order`."""
    try:
        data = api.list_user_orders(user_id, limit)
        return _ok({
            "count": data["count"],
            "orders": [
                {
                    "order_id": o["order_id"],
                    "status": o["status"],
                    "placed_on": o["placed_on"],
                    "total": o["total"],
                    "items": [i["name"] for i in o["items"]],
                }
                for o in data["orders"]
            ],
        })
    except APIError as e:
        return _err(e)


# ==========================================================================
# 3. RETURNS
# ==========================================================================
@tool("check_return_eligibility", args_schema=OrderIdInput)
def check_return_eligibility(order_id: str) -> str:
    """Checks whether an order is eligible for return (7-day window, delivered status)
    and displays which items are returnable. ALWAYS call this tool BEFORE invoking
    `create_return_request`."""
    try:
        return _ok(api.return_eligibility(order_id))
    except APIError as e:
        return _err(e)


class CreateReturnInput(BaseModel):
    order_id: str = Field(..., description="Order ID, e.g., 'ORD-2001'")
    product_id: str = Field(..., description="ID of the product being returned")
    reason: str = Field(..., description="Exactly one of: damaged, wrong_item, size_issue, not_as_described, changed_mind, defective")
    comment: Optional[str] = Field(None, description="Short explanation provided by the customer")
    qty: int = Field(1, description="Quantity of items to be returned")


@tool("create_return_request", args_schema=CreateReturnInput)
def create_return_request(order_id: str, product_id: str, reason: str,
                          comment: Optional[str] = None, qty: int = 1) -> str:
    """Creates a return/RMA request and returns the RMA ID, refund amount, and pickup date.
    WARNING: This is a WRITE action. Before invoking: (a) `check_return_eligibility` must be called,
    and (b) explicit confirmation must be obtained from the customer."""
    try:
        return _ok(api.create_return(order_id=order_id, product_id=product_id,
                                     reason=reason, comment=comment, qty=qty))
    except APIError as e:
        return _err(e)


class RmaInput(BaseModel):
    rma_id: str = Field(..., description="Return/RMA ID, e.g., 'RMA-5001'")


@tool("get_return_status", args_schema=RmaInput)
def get_return_status(rma_id: str) -> str:
    """Provides the current status and refund information for an already created return request."""
    try:
        return _ok(api.get_return(rma_id))
    except APIError as e:
        return _err(e)


# ==========================================================================
# 4. PERSONALIZED RECOMMENDATION
# ==========================================================================
class RecommendInput(BaseModel):
    user_id: Optional[str] = Field(None, description="Logged-in user ID -- used to make suggestions based on user taste and order history")
    product_id: Optional[str] = Field(None, description="Product ID -- used to suggest items similar to this specific product")
    budget_max: Optional[float] = Field(None, description="Customer's maximum budget in BDT")
    limit: int = Field(4, description="Number of suggestions required")


@tool("recommend_products", args_schema=RecommendInput)
def recommend_products(user_id: Optional[str] = None, product_id: Optional[str] = None,
                       budget_max: Optional[float] = None, limit: int = 4) -> str:
    """Provides personalized product suggestions. Use this tool for queries like 'suggest something for me',
'what else is similar to this', or 'give me some gift ideas'.
If searching with specific keywords, use `search_products` instead of this tool."""
    try:
        data = api.recommend(user_id=user_id, product_id=product_id,
                             budget_max=budget_max, limit=limit)
        return _ok({"count": data["count"], "results": [_slim_product(p) for p in data["results"]]})
    except APIError as e:
        return _err(e)


# ==========================================================================
# 5. POLICY / FAQ
# ==========================================================================
class PolicyInput(BaseModel):
    topic: str = Field(..., description="One of: return, refund, shipping, warranty, payment")


@tool("get_store_policy", args_schema=PolicyInput)
def get_store_policy(topic: str) -> str:
    """Fetches official store policy texts (return, refund, shipping, warranty, payment).
        Never generate answers to policy-related questions on your own -- always retrieve information using this tool."""
    try:
        return _ok(api.get_policy(topic))
    except APIError as e:
        return _err(e)


# ==========================================================================
# TOOL REGISTRY
# ==========================================================================
ALL_TOOLS: List = [
    search_products,
    get_product_details,
    check_stock,
    track_order,
    list_my_orders,
    check_return_eligibility,
    create_return_request,
    get_return_status,
    recommend_products,
    get_store_policy,
]

# Multi-agent setup er jonno domain-wise grouping
DISCOVERY_TOOLS = [search_products, get_product_details, check_stock, recommend_products]
ORDER_TOOLS = [track_order, list_my_orders, get_store_policy]
RETURN_TOOLS = [check_return_eligibility, create_return_request, get_return_status, get_store_policy]
