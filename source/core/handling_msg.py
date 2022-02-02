"""
In this module we process events related to bot (such as messages, requests)
"""
from io import BytesIO
from pathlib import Path

import sympy as sy
from telegram import Update
from telegram.ext import CallbackContext

from source.conf import Config
from source.math.calculus_parser import CalculusParser
from source.math.graph import Graph, DrawError
from source.math.graph_parser import GraphParser, ParseError

# We get "USE_LATEX" parameter from settings
SETTINGS = Config()

# A number of pixels per inch for TeX pictures
PPI = '600'


def echo(text: str):
    """On simple messages bot replies with echo"""
    return text + '!'


def send_graph(update: Update, context: CallbackContext):
    """User requested to draw a plot"""
    user = update.message.from_user
    resources_path = Path(__file__).resolve().parents[2] / "resources"
    file_path = resources_path / f"{user['id']}.png"
    if context.args:
        expr = " ".join(context.args).lower()
    else:
        expr = update.message.text.lower()
    parser = GraphParser()

    try:
        tokens = parser.parse(expr)
        graph = Graph(file_path)
        graph.draw(tokens)
    except (ParseError, DrawError) as err:
        update.message.reply_text(str(err))
        return

    with open(file_path, 'rb') as graph_file:
        output_message = "Here a graph of requested functions"
        if warning := '\n'.join(parser.warnings):
            output_message += f"\n{warning}"
            parser.clear_warnings()

        context.bot.send_photo(
            chat_id=user['id'],
            photo=graph_file,
            caption=output_message
        )


def send_analyse(update: Update, context: CallbackContext):
    """User requested some function analysis"""
    user = update.message.from_user
    expr = " ".join(context.args).lower()
    parser = CalculusParser()

    try:
        # Parse request and check if some template was found
        # If parser can't understand what user mean, it returns False
        is_pattern_found = parser.parse(expr)
        if not is_pattern_found:
            update.message.reply_text("Couldn't find a suitable template. Check the input.")
            return
        result = parser.process_query()

        # If USE_LATEX set in True, then send picture to the user. Else, send basic text
        if SETTINGS.properties["APP"]["USE_LATEX"]:
            latex = parser.make_latex(result)
            with BytesIO() as latex_picture:
                sy.preview(fr'${latex}$', output='png', viewer='BytesIO', outputbuffer=latex_picture,
                           dvioptions=['-D', PPI])
                latex_picture.seek(0)

                context.bot.send_photo(
                    chat_id=user['id'],
                    photo=latex_picture,
                    caption="\n".join(parser.warnings)
                )
        else:
            context.bot.send_message(
                chat_id=user['id'],
                text=str(result)
            )
        parser.clear_warnings()
    except RecursionError:
        update.message.reply_text("Incorrect input. Please check your function.")
    except (ParseError, ValueError, NotImplementedError) as err:
        update.message.reply_text(str(err))
