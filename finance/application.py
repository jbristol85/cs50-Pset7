import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    user = session["user_id"]
    transactions = []
    userAccount = db.execute('SELECT * FROM "users" WHERE "id" = :user', user = user)
    # print("*****", usd(userAccount[0]["cash"]))
    # stocks = db.execute('SELECT * FROM "stocks" WHERE "user" = :user', user = user)
    stocks = db.execute('SELECT * ,SUM(shares), "symbol" FROM stocks WHERE user = :user GROUP BY symbol', user = user)
    allStocksTotal = 0

    for stock in stocks:
        currentPrice = lookup(stock["symbol"])
        # print("currentPrice", currentPrice["price"])
        stock['shares'] = stock['SUM(shares)']
        stock["price"] = usd(currentPrice["price"])
        total = int(stock["shares"]) * currentPrice["price"]
        stock["total"] = usd(total)
        allStocksTotal += total
        stock["name"] = currentPrice["name"]
        transactions.append(stock)
        # print(transactions)

    portfolioTotal = allStocksTotal + userAccount[0]["cash"]
    return render_template('index.html', transactions = transactions, cash = usd(userAccount[0]["cash"]), total = usd(allStocksTotal), portfolio = usd(portfolioTotal))
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        if not request.form.get("symbol"):
            return apology("Please enter a Stock Symbol")
        elif not request.form.get("shares"):
            return apology("Please enter a quantity of shares")

        user = session["user_id"]
        symbol = request.form.get("symbol")
        try:
            shares = float(request.form.get("shares"))
        except ValueError:
            return apology("Please select a valid quantity")
        if shares < 0 or shares % 1 != 0:
            return apology("Please enter a valid quantity")
        quote = lookup(symbol)

        if not quote:
            return apology("Please enter a valid stock symbol")

        userAccount = db.execute('SELECT * FROM "users" WHERE "id" = :user', user = user)
        buyTotal = quote["price"] * shares
        userCash = userAccount[0]["cash"]
        remainingCash = userCash - buyTotal
        # print(buyTotal)
        # print(userCash)
        if userCash < buyTotal:
            return apology("Not enough money")
        else:
            db.execute('INSERT INTO "stocks" ("user","symbol","shares","price") VALUES (:user, :symbol, :shares, :price)', user = user, symbol = quote["symbol"], shares = shares, price = int(quote["price"]))
            db.execute('UPDATE users SET cash = cash - :buyTotal WHERE "id" = :user', buyTotal = buyTotal, user = user)
        return redirect("/")

    else:
       return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""

    user = session["user_id"]
    transactions = []
    userAccount = db.execute('SELECT * FROM "users" WHERE "id" = :user', user = user)
    # print("*****", usd(userAccount[0]["cash"]))
    stocks = db.execute('SELECT * FROM "stocks" WHERE "user" = :user', user = user)
    allStocksTotal = 0

    for stock in stocks:
        currentStock = lookup(stock["symbol"])
        # print("currentPrice", currentPrice["price"])
        # stock["price"] = usd(currentPrice["price"])
        total = int(stock["shares"]) * stock["price"]
        if total < 0:
            stock["buySale"] = "Sale"
        else:
            stock['buySale'] = "Buy"
        stock["total"] = usd(total)
        allStocksTotal += total
        stock["name"] = currentStock["name"]
        transactions.append(stock)
    return render_template("history.html", transactions = transactions)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":
        if not request.form.get("symbol"):
            return apology("Please enter a stock symbol")
        quote = lookup(request.form.get("symbol"))

        if not quote:
            return apology("Please enter a valid stock symbol")
        return render_template("display.html", name = quote["name"] , price = usd(quote["price"]), symbol = quote["symbol"])
    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Missing username")
        elif not request.form.get("password"):
            return apology("Missing password")
        elif not request.form.get("confirmation"):
            return apology("Missing Confirmation")
        elif not request.form.get("password") == request.form.get("confirmation"):
            return apology("Password and confirmation don't match")

        username = request.form.get("username")
        # print(username)
        hashPass = generate_password_hash(request.form.get("password"))
        # print(hashPass)
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashPass)", username = username, hashPass = hashPass)

        if not result:
            return apology("Not entered into Database")

        rows = db.execute("SELECT * FROM users WHERE username = :username", username=username)
        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():

    if request.method == "POST":
        # print("symbol**********", request.form.get("symbol"))
        quote = lookup(request.form.get("symbol"))
        # print(quote)

        if not request.form.get("symbol"):
            return apology("Please enter a Stock Symbol")
        elif not request.form.get("shares"):
            return apology("Please enter a quantity of shares")
        elif not quote:
            return apology("Please enter a valid stock symbol")

        user = session["user_id"]
        # print(user)
        symbol = request.form.get("symbol")
        try:
            shares = float(request.form.get("shares"))
        except ValueError:
            return apology("Please select a valid quantity")
        if shares < 0 or shares % 1 != 0:
            return apology("Please select a valid quantity")
        currentPrice = lookup(symbol)

        userAccount = db.execute('SELECT * FROM "users" WHERE "id" = :user', user = user)
        stockToSell = db.execute('SELECT * FROM "stocks" WHERE "user" = :user AND "symbol" LIKE :symbol', user = user, symbol = symbol)
        sellTotal = currentPrice['price'] * shares
        userCash = userAccount[0]["cash"]
        # print("sellTotal", sellTotal)
        # print(userCash)
        quantityOwned = db.execute('SELECT SUM(shares) FROM stocks WHERE user = :user AND symbol = :symbol', user = user, symbol = symbol)
        # print(quantityOwned[0]['SUM(shares)'])
        if quantityOwned[0]['SUM(shares)'] <= shares:
            return apology("Not enough stock")
        else:
            db.execute('INSERT INTO "stocks" ("user","symbol","shares","price") VALUES (:user, :symbol, :shares, :price)', user = user, symbol = symbol, shares = 0-shares, price = currentPrice["price"])
            db.execute('UPDATE "users" SET "cash"=:cash WHERE "id" = :user', cash = userCash + sellTotal, user = user)
            return redirect("/")

    else:
        user = session["user_id"]
        stocksToList = []
        userAccount = db.execute('SELECT * FROM "users" WHERE "id" = :user', user = user)
        # print("*****", usd(userAccount[0]["cash"]))
        # stocks = db.execute('SELECT * FROM "stocks" WHERE "user" = :user', user = user)
        stocks = db.execute('SELECT symbol FROM stocks WHERE user = :user GROUP BY symbol', user = user)
        stocksToList.append(stocks)
        # print(stocksToList)
        return render_template("sell.html", stocks = stocksToList[0])

@app.route("/deposit", methods=["GET", "POST"])
@login_required
def deposit():
    """Buy shares of stock"""

    if request.method == "POST":
        user = session["user_id"]
        depositAmount = request.form.get("depositAmount")

        if not depositAmount:
            return apology("Please enter an amount to deposit")
        userAccount = db.execute('SELECT * FROM "users" WHERE "id" = :user', user = user)
        userCash = userAccount[0]["cash"]
        db.execute('UPDATE "users" SET "cash"=:cash WHERE "id" = :user', cash = int(userCash) + int(depositAmount), user = user)
        return redirect("/")
    else:
        return render_template('deposit.html')

def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
