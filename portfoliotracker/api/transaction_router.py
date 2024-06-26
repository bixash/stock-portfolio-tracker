"""
-- Created by: Ashok Kumar Pant
-- Created on: 7/18/23
"""

import logging
import os
from fastapi.responses import RedirectResponse

from fastapi import APIRouter, Request, Form,  UploadFile, status
from portfoliotracker.repo.db import get_db_connection

from portfoliotracker.utils.utils import get_templates_directory, check_fileUploaded
from portfoliotracker.repo.user_repo import UserRepo
from portfoliotracker.service.user_service import UserService
from portfoliotracker.repo.transaction_repo import TransactionRepo
from portfoliotracker.service.transaction_service import TransactionService
from portfoliotracker.repo.company_repo import CompanyRepo
from portfoliotracker.service.company_service import CompanyService

from portfoliotracker.entities import User

from fastapi.templating import Jinja2Templates
from portfoliotracker.utils import Settings, get_templates_directory

router = APIRouter()

logger = logging.getLogger(__name__)

user_db = get_db_connection()
trans_db = get_db_connection()

company_db = get_db_connection()

user_repo = UserRepo(user_db)
user_service = UserService(user_repo=user_repo)

trans_repo = TransactionRepo(trans_db)
trans_service = TransactionService(trans_repo=trans_repo)


company_repo = CompanyRepo(company_db)
company_service = CompanyService(company_repo=company_repo)

templates = Jinja2Templates(directory=get_templates_directory())

@router.get("/transactions/all")
def get_transaction(request: Request):
    if not request.session["token"]:
        return templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
    token = request.session["token"]
    user_id = request.session['user_id']
    user = User(username = request.session["username"], user_id = request.session['user_id'])

    all_transactions = trans_service.all_transactions(user).result
    # print(all_transactions)
    
    return templates.TemplateResponse("history.html", { "request": request, "username": user.username, "all_transactions": all_transactions})

@router.get("/transactions/holdings")
def holdings(request: Request):
    if not request.session["token"]:
        return templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
    token = request.session["token"]
    user_id = request.session['user_id']


    user = User(username = request.session["username"], user_id = request.session['user_id'])

    distinctSymbol = trans_service.distinct_stockSymbols(user)
    if trans_service.holdings_stats(user, distinctSymbol):
        holdings_stats = trans_service.holdings_stats(user, distinctSymbol)
        holdings = trans_service.holdings_only(holdings_stats)
        company_stats = trans_service.company_stats(holdings_stats)

        holdings_summary = trans_service.holdings_summary(holdings)
        sector_instrumentList = trans_service.holdings_sector_instrument_list(company_stats)

        return templates.TemplateResponse("holdings.html", {"request": request, "username": user.username, "holdings": holdings, 'holdings_summary': holdings_summary, "sector_instrumentList":  sector_instrumentList})

    return templates.TemplateResponse("holdings.html", { "request": request,  "username": user.username, "holdings": []})

@router.get("/holdings/{sector}&{instrument}")
def select_holdings(sector:str, instrument: str, request: Request):
    if not request.session["token"]:
        return templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
    token = request.session["token"]

    user = User(username = request.session["username"], user_id = request.session['user_id'])

    distinctSymbol = trans_service.distinct_stockSymbols(user)
    if trans_service.holdings_stats(user, distinctSymbol):
        holdings_stats = trans_service.holdings_stats(user, distinctSymbol)
        holdings_only = trans_service.holdings_only(holdings_stats)
        company_stats = trans_service.company_stats(holdings_only)
        holdings = trans_service.holdings_sector_instrument(company_stats, sector, instrument)
       
        holdings_summary = trans_service.holdings_summary(holdings)

        sector_instrumentList = trans_service.holdings_sector_instrument_list(company_stats)

        return templates.TemplateResponse("holdings.html", { "request": request, "username": user.username, "holdings": holdings, 'holdings_summary': holdings_summary, "sector_instrumentList":  sector_instrumentList, 'sector':sector, 'instrument': instrument})

    return templates.TemplateResponse("holdings.html", { "request": request,  "username": user.username, "holdings": []})

@router.get("/transactions/upload")
def upload(request: Request):
    if not request.session["token"]:
        return  templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
    user = User(username = request.session["username"], user_id = request.session['user_id'])
    if trans_service.check_user_transactions(user):
        return templates.TemplateResponse("upload.html", {"request": request, "username": user.username, "msg":"Looks like you have already uploaded transactions details! So, if you upload new transactions, your old transactions will be deleted!", "uploaded": True})
    return templates.TemplateResponse("upload.html", {"request": request, "username": user.username, "uploaded": False})

@router.post("/transactions/upload")
def upload(request: Request, file: UploadFile):
    user = User(username = request.session["username"], user_id = request.session['user_id'])

    filename = file.filename
    file_location = f"{os.path.join(Settings.CSV_UPLOAD_PATH)}/{user.user_id}_{user.username}_transactions.csv"

    if not file:
        return templates.TemplateResponse("upload.html", {"request": request, "username": user.username, "msg": "No upload file sent!"})
    if filename == '':
        return templates.TemplateResponse("upload.html", {"request": request, "username": user.username, "msg": "No file selected!"})
    if not filename.endswith('.csv'):
        return templates.TemplateResponse("upload.html", {"request": request, "username": user.username, "msg": "File should be in .csv extension!"})
    
    if not check_fileUploaded(file_location, file):
        return templates.TemplateResponse("upload.html", {"request": request, "username": user.username, "msg": "File can't be uploaded!"})

    if trans_service.check_user_transactions(user):
        trans_repo.delete_transaction(user.user_id)
        
    response = trans_service.upload_transactions(user, file_location)
    if response.error:
        return templates.TemplateResponse("upload.html",{ "request": request, "msg": response.msg, "username": user.username})
    return RedirectResponse(url=request.url_for("portfolio"), status_code=status.HTTP_303_SEE_OTHER)

@router.post('/transactions/delete-data')
def delete_data(request: Request, password: str = Form()):
    if not request.session["token"]:
        return  templates.TemplateResponse("login.html", { "request": request, "msg":"Please login to continue!"})
    
    user = User(username = request.session["username"], user_id = request.session['user_id'])

    real = user_service.get_user(user.user_id).result

    if real.password == password:
        if trans_service.delete_transactions(user.user_id).success:
            return templates.TemplateResponse("profile.html", { "request": request,  "user_id": user.user_id, "username": user.username, "email": real.email, "msg": "Your transactions data was deleted permanently!"})
    else:
        return templates.TemplateResponse("profile.html", { "request": request,  "user_id": user.user_id, "username": user.username, "email": real.email, "msg": "Sorry password invalid!"})
    
@router.get("/transactions/sector-stats")
def get_sector_stats(request: Request):
    user = User(username = request.session["username"], user_id = request.session['user_id'])
    distinctSymbol = trans_service.distinct_stockSymbols(user)
    holdings_stats = trans_service.holdings_stats(user, distinctSymbol)
    company_stats = trans_service.company_stats(holdings_stats)
    sector_summary = trans_service.sector_summary(company_stats)
  
    return{"result": trans_service.XYarray(sector_summary)}

@router.get("/transactions/instrument-stats")
def get_instrument_stats(request: Request):
    user = User(username = request.session["username"], user_id = request.session['user_id'])
    distinctSymbol = trans_service.distinct_stockSymbols(user)
    holdings_stats = trans_service.holdings_stats(user, distinctSymbol)
    company_stats = trans_service.company_stats(holdings_stats)
    instrument_summary = trans_service.instrument_summary(company_stats)
    return{"result": trans_service.XYarray(instrument_summary)}