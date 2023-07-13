from flask import Blueprint, render_template, request, url_for, session, redirect
from werkzeug.utils import secure_filename
from methods import date_format, stringToInt, shorten_history, tupleToStr, ZeroBalancetoEmpty
from kittapi import UpdateStockPrices
import csv
import sqlite3
import os.path
# from kitta import getTodayPrice

con = sqlite3.connect("database.db", check_same_thread=False)
cur = con.cursor()

views = Blueprint('views', __name__)


@views.route('/')
def base():
   return render_template("base.html")


@views.route('/login', methods=['GET', 'POST'])
def login():
   if request.method == 'POST':
      email = request.form['email']
      password = request.form['password']

      cur.execute("SELECT id, username FROM `User` where email= ? and password = ?", (email, password))
      result = cur.fetchone()

      user_id = result[0]
      username = result[1]

      if result:
         session['user_id'] = user_id
         session['username'] = username
         return redirect(url_for('views.dashboard'))
      else:
         err_msg = "Username or password invalid!!"
         return render_template("login.html", msg = err_msg)

   return render_template("login.html")


@views.route('/signup', methods=['GET', 'POST'])
def signup():
   return render_template("signup.html")


@views.route('/dashboard')
def dashboard():
   if 'user_id' in session:
      user_id = session['user_id']

   if 'username' in session:
      user_name = session['username']
      
   UpdateStockPrices('https://api.kitta.dev/stocks/live') 
   
   # https://www.nepalipaisa.com/api/GetTodaySharePrice
   cur.execute("SELECT DISTINCT scrip FROM transactions where uid = ?", (user_id,))
   stock_symbols = cur.fetchall()

   transactions = []

   for stock in stock_symbols:
      stock = tupleToStr(stock)

      # cur.execute("SELECT  stock.scrip, balance_after_transaction, closing_price from stock where stock.scrip in( SELECT s FROM) FROM stock INNER JOIN transactions ON transactions.scrip = stock.scrip")

      # cur.execute("SELECT stock.scrip, balance_after_transaction from transactions where scrip = ? and uid = ? order by transaction_date desc limit 1", (stock, user_id, ))

      cur.execute("SELECT stock.scrip, balance_after_transaction, closing_price FROM stock INNER JOIN transactions ON transactions.scrip = stock.scrip where transactions.scrip = ? and uid = ? order by transaction_date desc limit 1", (stock, user_id, ))

      transactions.append(cur.fetchall())

   '''
    changing zero balance scrip to empty list and removing empty list 
   '''   
   result = list(filter(None, ZeroBalancetoEmpty(transactions)))
   
   return render_template("dashboard.html", transaction = result, username=user_name)


@views.route('/upload', methods=['GET','POST'])
def upload():
   if 'user_id' in session:
      user_id = session['user_id']
   
   path = './Transaction_History.csv'
   check_file = os.path.isfile(path)

   print(check_file)
   if check_file:
      # reading uploaded file
      with open('Transaction_History.csv', newline='') as csvfile:
         reader = csv.DictReader(csvfile)

         for row in reader:
            sn = row['S.N']
            scrip= row['Scrip']
            transaction_date = date_format(row['Transaction Date'])
            credit_quantity = stringToInt(row['Credit Quantity'])
            debit_quantity = stringToInt(row['Debit Quantity'])
            balance_after_transaction = stringToInt(row['Balance After Transaction'])
            history_description = shorten_history(row['History Description'])

            print(sn,scrip,transaction_date,credit_quantity,debit_quantity,balance_after_transaction,history_description, user_id)
            
            try:
               cur.execute("INSERT INTO transactions (id, scrip, transaction_date, credit_quantity, debit_quantity, balance_after_transaction, history_description, uid)values(?,?,?,?,?,?,?,?)", (sn, scrip,transaction_date, credit_quantity, debit_quantity, balance_after_transaction, history_description, user_id))
            except sqlite3.IntegrityError as e:
               print("Error occurred: ", e)
            

            con.commit()
      return redirect(url_for('views.dashboard'))
   if request.method == 'POST':
      f = request.files['file']
      f.save(secure_filename(f.filename))
      print(secure_filename(f.filename))

      return render_template(url_for('views.upload'))
   
   return render_template("upload.html")             