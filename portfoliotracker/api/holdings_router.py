import logging

from fastapi import APIRouter, Request
from portfoliotracker.repo.db import get_db_connection
from portfoliotracker.repo.transaction_repo import TransactionRepo
from portfoliotracker.service.transaction_service import TransactionService
from portfoliotracker.entities import User
from fastapi.templating import Jinja2Templates
from portfoliotracker.utils import get_templates_directory

router = APIRouter()

logger = logging.getLogger(__name__)

db = get_db_connection()
trans_repo = TransactionRepo(db)
trans_service = TransactionService(trans_repo=trans_repo)
templates = Jinja2Templates(directory=get_templates_directory())

@router.get("/holdings")
def get_transaction(request: Request):
    if not request.session["token"]:
        return templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
    token = request.session["token"]
    user_id = request.session['user_id']


    user = User(username = request.session["username"], user_id = request.session['user_id'])
    holdings = trans_service.get_balanced_transactions_with_prices(user)
  
    return templates.TemplateResponse("holdings.html", { "request": request, "username": user.username, "holdings": holdings.result,})