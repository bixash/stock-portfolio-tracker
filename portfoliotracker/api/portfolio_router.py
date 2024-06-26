
import logging

from fastapi import APIRouter, Request


from portfoliotracker.entities import User


from portfoliotracker.repo import TransactionRepo
from portfoliotracker.repo.auth_repo import AuthRepo
from portfoliotracker.repo.stock_repo import StockRepo
from portfoliotracker.repo.company_repo import CompanyRepo

from portfoliotracker.repo.db import get_db_connection

from portfoliotracker.service.auth_service import AuthService
from portfoliotracker.service.stock_service import StockService
from portfoliotracker.service.transaction_service import TransactionService
from portfoliotracker.service.company_service import CompanyService



from fastapi.templating import Jinja2Templates

import os

router = APIRouter()

logger = logging.getLogger(__name__)

auth_db = get_db_connection()
trans_db = get_db_connection()
stock_db = get_db_connection()
company_db = get_db_connection()
auth_repo = AuthRepo(auth_db)
auth_service = AuthService(auth_repo=auth_repo)

trans_repo = TransactionRepo(trans_db)
trans_service = TransactionService(trans_repo=trans_repo)

stock_repo = StockRepo(stock_db)
stock_service = StockService(stock_repo=stock_repo)

company_repo = CompanyRepo(company_db)
company_service = CompanyService(company_repo=company_repo)

templates_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "resources", "templates")
templates = Jinja2Templates(directory=templates_directory)

@router.get('/portfolio', name ="portfolio")
def portfolio(request: Request):
    if not request.session["token"]:
        return  templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
   
    user = User(username = request.session["username"], user_id = request.session['user_id'])


    '''update the database prices if only database trading-date is different'''

    if stock_service.get_stock_prices_from_api().success:
        if stock_repo.select_all_stock_prices():
            api_date = stock_service.get_stock_prices_from_api().result['result']['stocks'][1]['tradeDate']
            if stock_repo.check_tradeDate():
                db_date = stock_repo.get_stock_tradeDate()
                if not stock_service.is_tradeDate_same_db(api_date, db_date):
                    stock_service.update_prices_todb()  
        else:
            stock_service.insert_prices_todb()
                    

    if trans_service.check_user_transactions(user):
        distinctSymbol = trans_service.distinct_stockSymbols(user)
        holdings_stats = trans_service.holdings_stats(user, distinctSymbol)
        portfolio_summary = trans_service.portfolio_summary(holdings_stats)
        recent_transactions = trans_service.recent_transactions(user).result
        holdings_only = trans_service.holdings_only(holdings_stats)

        holdings_summary = trans_service.holdings_summary(holdings_only)
        instrument_summary = trans_service.instrument_summary(trans_service.company_stats(holdings_only))
        holdings_length = len(trans_service.holdings_only(holdings_stats))
    
        return templates.TemplateResponse("portfolio.html", { "request": request,  "recent_transactions": recent_transactions,"username": user.username, "holdings_summary": holdings_summary,  "portfolio_summary": portfolio_summary, "instrument_summary": instrument_summary, "holdings_length": holdings_length, "flag":False })
    
    return templates.TemplateResponse("portfolio.html", { "request": request,  "username": user.username, "flag": True})

