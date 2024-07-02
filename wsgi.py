from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_bootstrap import Bootstrap5
from flask_wtf import FlaskForm, CSRFProtect
from wtforms import StringField, RadioField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length
import csv
import pandas as pd
import numpy as np

"""
df = pd.read_csv("testing_poker_log.csv", sep="\t", header=None)
df[0] = (
    df[0].str.extract(r"Your hand is (.*?), (.*?),")[0]
    + ", "
    + df[0].str.extract(r"Your hand is (.*?), (.*?),")[1]
)
starting_hands = df.dropna()
output_file = "my_starting_hands.txt"
starting_hands.to_csv(output_file, index=False, header=False, sep="\t")
"""

starting_hand_path = "my_starting_hands.txt"
with open(starting_hand_path, "r") as file:
    lines = file.read().splitlines()

data = [line.split(", ") for line in lines]
starting_hand_df = pd.DataFrame(data, columns=["Card 1", "Card 2"])

my_starting_hands = []

for row in starting_hand_df.itertuples(index=True, name="Pandas"):
    suited = row._1[-1] == row._2[-1]
    starter_hand = row._1[0] + row._2[0]
    starter_hand = starter_hand.replace("1", "T")
    if suited:
        starter_hand += "s"
    else:
        starter_hand += "o"
    my_starting_hands.append(starter_hand)

# print(my_starting_hands)


def luckCalculation(players):
    luck = np.array([])
    for hand in my_starting_hands:
        equity_data = (
            Equity.query.filter_by(hand=hand).first()
            or Equity.query.filter_by(hand=hand[1] + hand[0] + hand[2]).first()
        )
        # print(hand, equity_data)
        if players == "2":
            luck = np.append(luck, float(equity_data.players_2.strip("%")) / 100)
        elif players == "6":
            luck = np.append(luck, float(equity_data.players_6.strip("%")) / 100)
        elif players == "9":
            luck = np.append(luck, float(equity_data.players_9.strip("%")) / 100)
    return luck, 1 / int(players)


app = Flask(__name__)
app.secret_key = "myNameIsMithil"

# Configuration for the SQLite database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///equity.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bootstrap = Bootstrap5(app)
csrf = CSRFProtect(app)


class Equity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hand = db.Column(db.String(10), nullable=False)
    players_2 = db.Column(db.String(10), nullable=False)
    players_6 = db.Column(db.String(10), nullable=False)
    players_9 = db.Column(db.String(10), nullable=False)


# Run this once to create the database
"""with app.app_context():
    db.create_all()"""


def populate_db():
    with app.app_context():
        with open("starting_hand_equity.csv", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                equity = Equity(
                    hand=row["hand"],
                    players_2=row["players_2"],
                    players_6=row["players_6"],
                    players_9=row["players_9"],
                )
                db.session.add(equity)
            db.session.commit()


# Uncomment the following line to populate the database
# populate_db()


class NameForm(FlaskForm):
    starting = StringField(
        "What is your starting hand?", validators=[DataRequired(), Length(min=3, max=3)]
    )
    players = RadioField(
        "Choose number of players:",
        validators=[InputRequired(message=None)],
        choices=[
            ("2", "2 players"),
            ("6", "6 players"),
            ("9", "9 players"),
        ],
    )
    submit = SubmitField("Submit")


@app.route("/", methods=["GET", "POST"])
def index():
    form = NameForm()
    equity_data = None
    starting = None
    luck = None
    if form.validate_on_submit():
        starting = form.starting.data.upper()[:2] + form.starting.data[-1]
        equity_data = (
            Equity.query.filter_by(hand=starting).first()
            or Equity.query.filter_by(
                hand=starting[1] + starting[0] + starting[2]
            ).first()
        )
        luck, predicted_average = luckCalculation(form.players.data)
        my_average = np.sum(luck) / luck.size
        my_number_of_hands = luck.size
        my_standard_deviation = np.std(luck)
        my_predicted_average = predicted_average
    return render_template(
        "index.html",
        form=form,
        equity_data=equity_data,
        starting=starting,
        my_average=my_average,
        my_number_of_hands=my_number_of_hands,
        my_standard_deviation=my_standard_deviation,
        my_predicted_average=my_predicted_average,
    )


if __name__ == "__main__":
    app.run(debug=True)
