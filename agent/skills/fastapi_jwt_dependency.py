"""
FastAPI dependency that validates JWT Bearer token and returns the current user.
Use for: any new protected route. Import get_current_user from routes/auth.py (already exists).

Saved by agent on 2026-03-16.
"""

# Pattern: protected route
from fastapi import Depends
from ..routes.auth import get_current_user  # already exists in the codebase


# Usage in any router:
# @router.get("/my-protected-route")
# async def my_route(current_user: dict = Depends(get_current_user)):
#     user_id = str(current_user["_id"])
#     plan = current_user.get("plan", "free")
#     return {"user": user_id, "plan": plan}

# Pro-only route pattern:
# @router.get("/pro-only")
# async def pro_route(current_user: dict = Depends(get_current_user)):
#     if current_user.get("plan") != "pro" or current_user.get("subscription_status") != "active":
#         raise HTTPException(status_code=403, detail="Pro subscription required")
#     # ... pro logic
