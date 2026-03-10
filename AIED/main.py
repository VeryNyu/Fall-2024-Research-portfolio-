from customtkinter import *
from PIL import Image
from data import DataHandling as DH
import requests
from tkinter import messagebox, filedialog

import test as T

# #Configuration
# BACKEND_URL = "http://localhost:5000/chatgpt"

set_appearance_mode("light")
app = CTk()
app.geometry("800x550")


#main page
set_appearance_mode("light")
app = CTk()
app.title("Card Epiphany Selector")

# Load data
PROTO_DATA  = DH.load_json("epiphanies.json")   # Raw epiphany data keyed by character

effects_df = DH.load_csv("effects.csv")

effects_df.columns = [f"col{i}" for i in range(len(effects_df.columns))]
effects_df = effects_df.rename(columns={"col0": "name", "col1": "type", "col2": "description"})

# State
selected_character = None
selected_card      = None
choice_index       = None   # which epiphany choice the player picked

#Data Access
def get_epiphany_cards(character: str) -> list[str]:
    """Return card names that have epiphany options for this character."""
    char_data = PROTO_DATA.get(character, [])
    names = []
    for entry in char_data:
        if isinstance(entry, str):
            names.append(entry)
    return names

def get_epiphany_options(character: str, card_name: str) -> list[dict]:
    """Return the list of epiphany options for a given card."""
    char_data = PROTO_DATA.get(character, [])
    return char_data[card_name] if card_name in char_data else []

def create_main_page():
    global char_var, card_var, main_frame

    main_frame = CTkFrame(app)
    main_frame.pack(fill="both", expand=True, padx=30, pady=30)

    CTkLabel(main_frame, text="Card Epiphany Selector",
             font=CTkFont(size=22, weight="bold")).pack(pady=(10, 4))
    CTkLabel(main_frame,
             text="Choose a combatant and a card that has triggered an upgrade.",
             font=CTkFont(size=13)).pack(pady=(0, 20))

    # Character dropdown
    CTkLabel(main_frame, text="Combatant", font=CTkFont(size=14, weight="bold")).pack()
    char_var = StringVar(value="Select combatant…")
    char_menu = CTkOptionMenu(
        main_frame, variable=char_var,
        values=list(PROTO_DATA.keys()),
        width=260, command=on_character_select
    )
    char_menu.pack(pady=(4, 16))

    # Card dropdown (populated after character is chosen)
    CTkLabel(main_frame, text="Card with Epiphany", font=CTkFont(size=14, weight="bold")).pack()
    card_var = StringVar(value="Select card…")
    global card_menu
    card_menu = CTkOptionMenu(
        main_frame, variable=card_var,
        values=["Select combatant first"],
        width=260
    )
    card_menu.pack(pady=(4, 24))

    CTkButton(main_frame, text="Show Epiphany Choices",
              width=220, command=start_epiphany).pack(pady=6)


def on_character_select(character: str):
    options = get_epiphany_cards(character)
    if options:
        card_menu.configure(values=options)
        card_var.set("Select card…")
    else:
        card_menu.configure(values=["No epiphany cards found"])
        card_var.set("No epiphany cards found")


def start_epiphany():
    global selected_character, selected_card
    selected_character = char_var.get()
    selected_card      = card_var.get()

    if selected_character == "Select combatant…":
        messagebox.showerror("Error", "Please select a combatant.")
        return
    if selected_card in ("Select card…", "Select combatant first", "No epiphany cards found"):
        messagebox.showerror("Error", "Please select a valid card.")
        return

    options = get_epiphany_options(selected_character, selected_card)
    if not options:
        messagebox.showerror("Error", "No epiphany options found for this card.")
        return

    main_frame.destroy()
    show_epiphany_page(selected_character, selected_card, options)


# ─────────────────────────── Epiphany Page ───────────────────────
def show_epiphany_page(character: str, card_name: str, options: list[dict]):
    outer = CTkFrame(app)
    outer.pack(fill="both", expand=True, padx=20, pady=20)

    # ── Header ──
    header_text = (
        f"You are playing  {character}  and triggered an upgrade\n"
        f"for  \"{card_name}\".\n\nHere are your choices:"
    )
    CTkLabel(outer, text=header_text,
             font=CTkFont(size=15, weight="bold"),
             justify="center").pack(pady=(10, 6))

    # Scrollable choice list
    scroll = CTkScrollableFrame(outer)
    scroll.pack(fill="both", expand=True, padx=10, pady=6)

    choice_frames = []

    def select_choice(idx: int):
        # Highlight selected, grey out others
        for i, cf in enumerate(choice_frames):
            color = "#2b7a4b" if i == idx else "#3a3a3a"
            cf.configure(fg_color=color)
        result_label.configure(
            text=f"✔  You selected Choice {idx + 1}: {options[idx]['effect']}"
        )

    for i, opt in enumerate(options):
        type_color = {
            "Attack":  "#8b1a1a",
            "Skill":   "#1a4a8b",
            "Upgrade": "#5a3a8b",
        }.get(opt.get("type", ""), "#3a3a3a")

        cf = CTkFrame(scroll, corner_radius=10, fg_color="#3a3a3a")
        cf.pack(fill="x", padx=6, pady=5)
        choice_frames.append(cf)

        # Number badge
        CTkLabel(cf, text=str(i + 1),
                 font=CTkFont(size=18, weight="bold"),
                 width=36, text_color="white").grid(
            row=0, column=0, rowspan=2, padx=(10, 4), pady=10)

        # Type pill
        CTkLabel(cf,
                 text=f"  {opt.get('type', '?')}  ",
                 font=CTkFont(size=11, weight="bold"),
                 text_color="white",
                 fg_color=type_color,
                 corner_radius=8,
                 width=70).grid(row=0, column=1, sticky="w", padx=4, pady=(8, 2))

        # Cost
        cost_str = f"Cost: {opt.get('cost', '?')}"
        CTkLabel(cf, text=cost_str,
                 font=CTkFont(size=11),
                 text_color="#cccccc").grid(row=0, column=2, sticky="w", padx=8, pady=(8, 2))

        # Effect text
        CTkLabel(cf,
                 text=opt.get("effect", ""),
                 font=CTkFont(size=13),
                 text_color="white",
                 wraplength=560,
                 justify="left").grid(row=1, column=1, columnspan=3,
                                      sticky="w", padx=4, pady=(0, 8))

        # Select button
        btn_idx = i
        CTkButton(cf, text="Select", width=80,
                  fg_color="#555", hover_color="#2b7a4b",
                  command=lambda idx=btn_idx: select_choice(idx)).grid(
            row=0, column=4, rowspan=2, padx=10, pady=10)

        cf.grid_columnconfigure(3, weight=1)

    # Result banner
    result_label = CTkLabel(outer, text="",
                            font=CTkFont(size=13, weight="bold"),
                            text_color="#2db86a",
                            wraplength=720, justify="center")
    result_label.pack(pady=(4, 6))

    # Bottom buttons 
    btn_row = CTkFrame(outer, fg_color="transparent")
    btn_row.pack(pady=(2, 6))

    CTkButton(btn_row, text="← Back", width=130,
              fg_color="#555", hover_color="#333",
              command=lambda: [outer.destroy(), create_main_page()]).pack(
        side="left", padx=8)

    CTkButton(btn_row, text="Confirm & Restart", width=160,
              command=lambda: confirm_and_restart(outer)).pack(
        side="left", padx=8)


def confirm_and_restart(frame):
    frame.destroy()
    create_main_page()

#Initialize app
create_main_page()
app.mainloop()
