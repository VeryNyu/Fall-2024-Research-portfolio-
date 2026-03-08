from customtkinter import *
from PIL import Image
import data.jsonHandling as JH
import pandas as pd
import random
import requests
from tkinter import messagebox

import test as T

# #Configuration
# BACKEND_URL = "http://localhost:5000/chatgpt"

set_appearance_mode("light")
app = CTk()
app.geometry("700x450")
app.title("CSUSM Data Entry")

json_files = JH.load_all_json()

# student_data = pd.read_csv("Student ID DATA BASE(Sheet1).csv")
# cs211_json_path = "CS211.json"
# cs311_json_path = "CS311.json"

# T.print_dict(json_files)
combatant = JH.pick_random_key(json_files["combatants_data"])
deck = json_files["decks_data"][combatant]["cards"]
epiphanies = dict()
for key, value in json_files["epiphanies_data"][combatant].items():
    epiphanies.update({key: value})
sample = dict()
for key, value in epiphanies.items():
    sample[key] = JH.pick_random_sample(value, 3)
T.print_dict(sample)
# current_question_index = 0
# chosen_examples = {}
# ratings = {}  # Store 1-5 star ratings per question
# questions_data = []

# #AI Call
# def call_ai(question, student_answer, examples):
#     try:
#         r = requests.post(
#             BACKEND_URL,
#             json={
#                 "question": question,
#                 "studentInput": student_answer,
#                 "examples": examples
#             },
#             timeout=30
#         )
#         return r.json()["response"]
#     except Exception as e:
#         return f"AI Error: {e}"

# #Rate Answer
# def rate_answer(stars):
#     ratings[current_question_index] = stars
#     messagebox.showinfo(
#         "Rating Saved",
#         f"You rated Question {current_question_index + 1} as {stars} star(s)."
#     )

#main page
def create_main_page():
    global name_entry, id_entry, check_211, check_311, main_frame

    main_frame = CTkFrame(app)
    main_frame.pack(fill="both", expand=True, padx=20, pady=20)

    # logo = Image.open("Official_CSUSM_Logo.png").resize((200, 80))
    # logo_img = CTkImage(logo, size=(200, 80))
    # CTkLabel(main_frame, image=logo_img, text="").pack(pady=15)

    name_entry = CTkEntry(main_frame, placeholder_text="Student Name")
    name_entry.pack(pady=5)

    id_entry = CTkEntry(main_frame, placeholder_text="Student ID")
    id_entry.pack(pady=5)

    # check_211 = CTkCheckBox(main_frame, text="CS211")
    # check_211.pack()
    # check_311 = CTkCheckBox(main_frame, text="CS311")
    # check_311.pack()

    CTkButton(main_frame, text="Start", command=start).pack(pady=15)

#start function
def start():
    # sid = id_entry.get()
    # if sid not in student_data["studentID"].astype(str).values:
    #     messagebox.showerror("Error", "Invalid Student ID")
    #     return

    # if check_211.get():
    #     load_questions(cs211_json_path)
    # elif check_311.get():
    #     load_questions(cs311_json_path)
    # else:
    #     messagebox.showerror("Error", "Select course")
    #     return

    show_questions()

# -------------------- LOAD QUESTIONS --------------------
# def load_questions(path):
#     global questions_data
#     with open(path) as f:
#         questions_data = json.load(f)["questions"]


def show_questions():
    global left_display, left_input, right_display, next_btn

    main_frame.destroy()
    frame = CTkFrame(app)
    frame.pack(fill="both", expand=True)

    #Left Fram
    left = CTkFrame(frame)
    left.pack(side="left", expand=True, fill="both")
    left_display = CTkTextbox(left)
    left_display.pack(expand=True, fill="both", padx=10, pady=5)
    left_display.configure(state="disabled")

    left_input = CTkTextbox(left)
    left_input.pack(expand=True, fill="both", padx=10, pady=5)

    next_btn = CTkButton(left, text="Next", command=next_question)
    next_btn.pack(pady=10)

    #Right Frame
    right = CTkFrame(frame)
    right.pack(side="right", expand=True, fill="both")
    right_display = CTkTextbox(right)
    right_display.pack(expand=True, fill="both", padx=10, pady=5)
    right_display.configure(state="disabled")

    #Rating Buttons
    rating_frame = CTkFrame(right)
    rating_frame.pack(pady=10, fill="x")

    button_style = {"width": 40, "height": 30, "corner_radius": 20}

    one_star_button = CTkButton(rating_frame, text="1 ★", **button_style, command=lambda: rate_answer(1))
    one_star_button.grid(row=0, column=0, padx=2)
    two_star_button = CTkButton(rating_frame, text="2 ★", **button_style, command=lambda: rate_answer(2))
    two_star_button.grid(row=0, column=1, padx=2)
    three_star_button = CTkButton(rating_frame, text="3 ★", **button_style, command=lambda: rate_answer(3))
    three_star_button.grid(row=0, column=2, padx=2)
    four_star_button = CTkButton(rating_frame, text="4 ★", **button_style, command=lambda: rate_answer(4))
    four_star_button.grid(row=0, column=3, padx=2)
    five_star_button = CTkButton(rating_frame, text="5 ★", **button_style, command=lambda: rate_answer(5))
    five_star_button.grid(row=0, column=4, padx=2)

    for i in range(5):
        rating_frame.grid_columnconfigure(i, weight=1)

    # display_question(0)

#Display question
def display_question(i):
    # q = questions_data[i]
    # examples = chosen_examples.setdefault(
    #     i, [random.choice(q.get("examples", [""])) for _ in q["question"].split("{}")[:-1]]
    # )
    # text = q["question"].format(*examples)

    left_display.configure(state="normal")
    left_display.delete("1.0", "end")
    # left_display.insert("1.0", text)
    left_display.configure(state="disabled")
    left_input.delete("1.0", "end")  # Clear previous input

#Next question
def next_question():
    # global current_question_index

    # answer = left_input.get("1.0", "end").strip()
    # q = questions_data[current_question_index]
    # examples = chosen_examples[current_question_index]
    # question_text = q["question"].format(*examples)

    # feedback = call_ai(question_text, answer, examples)

    right_display.configure(state="normal")
    right_display.delete("1.0", "end")
    # right_display.insert("1.0", feedback)
    right_display.configure(state="disabled")

    # # Check if last question
    # if current_question_index < len(questions_data) - 1:
    #     current_question_index += 1
    #     display_question(current_question_index)
    # else:
    #     # User finished all questions
    #     messagebox.showinfo("Completed", "You have finished all questions!")
    #     left_input.configure(state="disabled")
    #     next_btn.configure(state="disabled")
    #     show_restart_button()

#Restart quiz Button 
def show_restart_button():
    restart_btn = CTkButton(app, text="Restart Quiz", command=restart_quiz)
    restart_btn.pack(pady=10)

def restart_quiz():
    global current_question_index, chosen_examples, ratings
    current_question_index = 0
    chosen_examples = {}
    ratings = {}
    for widget in app.winfo_children():
        widget.destroy()
    create_main_page()

#Initialize app
# create_main_page()
# app.mainloop()
