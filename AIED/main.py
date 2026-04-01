from customtkinter import *
from data import DataHandling as DH
import requests
import threading
from tkinter import messagebox

# ─── Config ───────────────────────────────────────────────────────────────────
BACKEND_URL = "http://localhost:5000/chatgpt"

# ─── App window ───────────────────────────────────────────────────────────────
set_appearance_mode("light")
app = CTk()
app.geometry("900x600")
app.title("Card Epiphany Selector")
app.resizable(False, False)

# ─── Load data ────────────────────────────────────────────────────────────────
EPIPHANY_DATA = DH.load_json("epiphanies.json")   # {char: {card_name: [opts]}}
CARDS_DATA    = DH.load_json("cards.json")         # {char: [{name,cost,type,effects,epiphanies}]}
DECKS_DATA    = DH.load_json("decks.json")         # {char: {skill, cards:[...]}}

# ─── Session state ────────────────────────────────────────────────────────────
selected_character : str  | None = None
selected_card_name : str  | None = None
selected_epiphany  : dict | None = None

# ─── Shared colours ───────────────────────────────────────────────────────────
TYPE_COLORS = {
    "Attack":  "#7a1818",
    "Skill":   "#17417a",
    "Upgrade": "#4a2a7a",
}


# ═══════════════════════════════════════════════════════════════════════════════
#  Data helpers
# ═══════════════════════════════════════════════════════════════════════════════

def get_character_cards(character: str) -> list[dict]:
    return CARDS_DATA.get(character, [])


def get_epiphany_options(character: str, card_name: str) -> list[dict]:
    return EPIPHANY_DATA.get(character, {}).get(card_name, [])


def call_ai(character: str, card_name: str, epiphany: dict,
            user_reason: str) -> str:
    """Send the player's choice + their reasoning to the AI backend."""
    prompt = (
        f"In a tactical card game, the character '{character}' triggered an epiphany "
        f"upgrade for the card '{card_name}'.\n\n"
        f"The player chose:\n"
        f"  Effect : {epiphany.get('effect', '?')}\n"
        f"  Type   : {epiphany.get('type', '?')}\n"
        f"  Cost   : {epiphany.get('cost', '?')}\n\n"
        f"The player explained their decision as follows:\n\"{user_reason}\"\n\n"
        f"Evaluate the player's reasoning and give concise tactical feedback on "
        f"whether this is a strong choice and how to play it effectively."
    )
    try:
        r = requests.post(
            BACKEND_URL,
            json={"question": prompt, "studentInput": user_reason, "examples": []},
            timeout=15,
        )
        return r.json().get("response", "No response from AI.")
    except requests.exceptions.ConnectTimeout:
        return "AI Error: Connection timed out."
    except requests.exceptions.ConnectionError:
        return "AI Error: Could not connect to backend. Is it running?"
    except Exception as e:
        return f"AI Error: {e}"


# ═══════════════════════════════════════════════════════════════════════════════
#  Shared: progress breadcrumb
# ═══════════════════════════════════════════════════════════════════════════════

def _progress_bar(parent: CTkFrame, step: int):
    """3-step breadcrumb strip at the top of every page (always row=0, grid)."""
    bar = CTkFrame(parent, fg_color=("#dddddd", "#2a2a3a"), height=38, corner_radius=0)
    bar.grid(row=0, column=0, sticky="ew")   # grid so siblings can also use grid

    steps = ["1  Combatant", "2  Cards", "3  Epiphany"]
    for i, label in enumerate(steps, start=1):
        is_active = (i == step)
        CTkLabel(
            bar,
            text=label,
            font=CTkFont(size=12, weight="bold" if is_active else "normal"),
            text_color="#ffffff" if is_active else "#aaaaaa",
            fg_color="#2b5ea0" if is_active else "transparent",
            corner_radius=6,
            padx=14, pady=4,
        ).pack(side="left", padx=6, pady=5)   # pack is fine *inside* bar


# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOW 1 — Combatant Select
# ═══════════════════════════════════════════════════════════════════════════════

def show_window1():
    """Landing page: pick a combatant, then press Start."""
    global selected_character, selected_card_name, selected_epiphany
    selected_character = None
    selected_card_name = None
    selected_epiphany  = None

    page = CTkFrame(app)
    page.pack(fill="both", expand=True)
    page.grid_columnconfigure(0, weight=1)

    _progress_bar(page, step=1)

    # Centre column (place mixes fine with grid on the same parent)
    centre = CTkFrame(page, fg_color="transparent")
    centre.place(relx=0.5, rely=0.5, anchor="center")

    CTkLabel(
        centre, text="Card Epiphany Selector",
        font=CTkFont(size=28, weight="bold"),
    ).pack(pady=(0, 10))

    CTkLabel(
        centre,
        text="Select your combatant to begin.",
        font=CTkFont(size=14),
        text_color="#666666",
    ).pack(pady=(0, 36))

    char_var = StringVar(value="Select combatant…")
    CTkOptionMenu(
        centre,
        variable=char_var,
        values=list(CARDS_DATA.keys()),
        width=300,
        font=CTkFont(size=13),
        dynamic_resizing=False,
    ).pack(pady=(0, 40))

    def on_start():
        global selected_character
        val = char_var.get()
        if val == "Select combatant…":
            messagebox.showerror("Error", "Please select a combatant before continuing.")
            return
        selected_character = val
        page.destroy()
        show_window2()

    CTkButton(
        centre, text="Start  →", width=220, height=46,
        font=CTkFont(size=16, weight="bold"),
        fg_color="#2b5ea0", hover_color="#3a7ad0",
        command=on_start,
    ).pack()


# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOW 2 — Deck Card Display
# ═══════════════════════════════════════════════════════════════════════════════

def show_window2():
    """Full deck of the chosen combatant. Only epiphany cards can be selected."""
    page = CTkFrame(app)
    page.pack(fill="both", expand=True)
    page.grid_rowconfigure(2, weight=1)   # row 0=progress, 1=header, 2=scroll, 3=nav
    page.grid_columnconfigure(0, weight=1)

    _progress_bar(page, step=2)

    # ── Sub-header ────────────────────────────────────────────────────────────
    hdr = CTkFrame(page, fg_color="transparent")
    hdr.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 6))
    hdr.grid_columnconfigure(0, weight=1)

    CTkLabel(
        hdr,
        text=f"{selected_character}  —  Deck Cards",
        font=CTkFont(size=18, weight="bold"),
    ).pack(side="left")

    skill_name = DECKS_DATA.get(selected_character, {}).get("skill", "")
    if skill_name:
        CTkLabel(
            hdr,
            text=f"  ⭐ Skill: {skill_name}  ",
            font=CTkFont(size=11, weight="bold"),
            text_color="white", fg_color="#1a3a6b",
            corner_radius=8,
        ).pack(side="left", padx=14)

    CTkLabel(
        hdr,
        text="Cards marked  ✦  have epiphany upgrades.",
        font=CTkFont(size=11),
        text_color="#888888",
    ).pack(side="right")

    # ── Card scroll ───────────────────────────────────────────────────────────
    scroll = CTkScrollableFrame(page, corner_radius=10)
    scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 6))

    cards     = get_character_cards(selected_character)
    epi_set   = set(EPIPHANY_DATA.get(selected_character, {}).keys())
    deck_list = DECKS_DATA.get(selected_character, {}).get("cards", [])

    card_frames: list[tuple[CTkFrame, str]] = []

    def _select_card(name: str):
        global selected_card_name
        selected_card_name = name
        for cf, n in card_frames:
            has_e = n in epi_set
            if n == name:
                cf.configure(fg_color="#1f5c38")
            else:
                cf.configure(fg_color=("#dde0f0", "#25253a") if has_e
                             else ("#e8e8e8", "#1e1e2e"))

    for card in cards:
        name    = card["name"]
        cost    = card.get("cost")
        ctype   = card.get("type", "?")
        effects = card.get("effects", "")
        has_epi = name in epi_set
        count   = deck_list.count(name)
        tc      = TYPE_COLORS.get(ctype, "#3a3a3a")
        bg      = ("#dde0f0", "#25253a") if has_epi else ("#e8e8e8", "#1e1e2e")

        cf = CTkFrame(scroll, corner_radius=8, fg_color=bg)
        cf.pack(fill="x", padx=4, pady=3)
        card_frames.append((cf, name))

        top = CTkFrame(cf, fg_color="transparent")
        top.pack(fill="x", padx=8, pady=(6, 2))

        # Type pill
        CTkLabel(
            top, text=f"  {ctype}  ",
            font=CTkFont(size=10, weight="bold"),
            text_color="white", fg_color=tc,
            corner_radius=6, width=64,
        ).pack(side="left")

        # Name
        CTkLabel(
            top, text=name,
            font=CTkFont(size=13, weight="bold"),
        ).pack(side="left", padx=8)

        # Cost
        if cost is not None:
            CTkLabel(
                top, text=f"[{cost}]",
                font=CTkFont(size=11), text_color="#888888",
            ).pack(side="left")

        # Duplicate badge
        if count > 1:
            CTkLabel(
                top, text=f" ×{count}",
                font=CTkFont(size=11, weight="bold"),
                text_color="#e0a020",
            ).pack(side="left", padx=4)

        # Epiphany marker / Select button
        if has_epi:
            CTkLabel(
                top, text="  ✦ Epiphany",
                font=CTkFont(size=11, weight="bold"),
                text_color="#cc88ff",
            ).pack(side="left", padx=8)

            CTkButton(
                top, text="Select", width=84,
                fg_color="#7030a0", hover_color="#9040c0",
                font=CTkFont(size=11, weight="bold"),
                command=lambda n=name: _select_card(n),
            ).pack(side="right", padx=4)
        else:
            CTkLabel(
                top, text="No Epiphany",
                font=CTkFont(size=10), text_color="#aaaaaa",
            ).pack(side="right", padx=8)

        # Effects
        CTkLabel(
            cf, text=effects,
            font=CTkFont(size=11),
            text_color=("#444444", "#bbbbbb"),
            wraplength=760, justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 6))

    # ── Navigation ────────────────────────────────────────────────────────────
    nav = CTkFrame(page, fg_color="transparent")
    nav.grid(row=3, column=0, pady=(4, 12))

    CTkButton(
        nav, text="← Back", width=120,
        fg_color="#555555", hover_color="#333333",
        command=lambda: [page.destroy(), show_window1()],
    ).pack(side="left", padx=10)

    def on_finish():
        if not selected_card_name:
            messagebox.showerror(
                "No Card Selected",
                "Please select a  ✦ Epiphany  card before continuing.",
            )
            return
        page.destroy()
        show_window3()

    CTkButton(
        nav, text="Finish  →", width=160, height=40,
        font=CTkFont(size=13, weight="bold"),
        fg_color="#2b5ea0", hover_color="#3a7ad0",
        command=on_finish,
    ).pack(side="left", padx=10)


# ═══════════════════════════════════════════════════════════════════════════════
#  WINDOW 3 — Epiphany Choices + User Explanation + AI Feedback
# ═══════════════════════════════════════════════════════════════════════════════

def show_window3():
    """Show epiphany options, collect the player's reasoning, submit to AI."""
    options = get_epiphany_options(selected_character, selected_card_name)
    if not options:
        messagebox.showerror("Error",
                             f"No epiphany options found for '{selected_card_name}'.")
        show_window2()
        return

    page = CTkFrame(app)
    page.pack(fill="both", expand=True)
    page.grid_rowconfigure(2, weight=1)   # row 0=progress, 1=header, 2=body, 3=nav
    page.grid_columnconfigure(0, weight=1)

    _progress_bar(page, step=3)

    # ── Header ────────────────────────────────────────────────────────────────
    CTkLabel(
        page,
        text=(f"{selected_character}  —  "
              f"Epiphany Upgrade for  \"{selected_card_name}\""),
        font=CTkFont(size=17, weight="bold"),
    ).grid(row=1, column=0, pady=(12, 6))

    # ── Two-column body ───────────────────────────────────────────────────────
    body = CTkFrame(page, fg_color="transparent")
    body.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 6))
    body.grid_columnconfigure(0, weight=1)
    body.grid_columnconfigure(1, weight=1)
    body.grid_rowconfigure(0, weight=1)

    # ─────────────────────────────────────────────────────────────────────────
    #  LEFT — epiphany choice list
    # ─────────────────────────────────────────────────────────────────────────
    left = CTkFrame(body, corner_radius=10, fg_color=("#f0f0f0", "#1c1c2e"))
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
    left.grid_rowconfigure(1, weight=1)
    left.grid_columnconfigure(0, weight=1)

    CTkLabel(
        left, text="Choose an Upgrade",
        font=CTkFont(size=14, weight="bold"),
    ).grid(row=0, column=0, pady=(10, 4))

    epi_scroll = CTkScrollableFrame(left, corner_radius=8)
    epi_scroll.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    choice_frames: list[CTkFrame] = []
    chosen_idx   = [None]   # list so closure can mutate it

    def _pick(idx: int):
        global selected_epiphany
        selected_epiphany = options[idx]
        chosen_idx[0]     = idx
        for i, cf in enumerate(choice_frames):
            cf.configure(
                fg_color="#1f5c38" if i == idx else ("#d8d8e8", "#2e2e3e")
            )

    for i, opt in enumerate(options):
        tc    = TYPE_COLORS.get(opt.get("type", ""), "#3a3a3a")
        otype = opt.get("type", "?")
        cost  = opt.get("cost", "?")
        eff   = opt.get("effect", "")

        cf = CTkFrame(epi_scroll, corner_radius=8,
                      fg_color=("#d8d8e8", "#2e2e3e"))
        cf.pack(fill="x", padx=2, pady=3)
        choice_frames.append(cf)

        hdr = CTkFrame(cf, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(6, 2))

        CTkLabel(
            hdr, text=str(i + 1),
            font=CTkFont(size=15, weight="bold"), width=24,
        ).pack(side="left")

        CTkLabel(
            hdr, text=f"  {otype}  ",
            font=CTkFont(size=10, weight="bold"),
            text_color="white", fg_color=tc,
            corner_radius=6, width=64,
        ).pack(side="left", padx=6)

        CTkLabel(
            hdr, text=f"Cost: {cost}",
            font=CTkFont(size=11), text_color="#888888",
        ).pack(side="left", padx=4)

        CTkButton(
            hdr, text="Select", width=72,
            fg_color="#555555", hover_color="#1f5c38",
            font=CTkFont(size=10),
            command=lambda idx=i: _pick(idx),
        ).pack(side="right")

        CTkLabel(
            cf, text=eff,
            font=CTkFont(size=11),
            text_color=("#333333", "#dddddd"),
            wraplength=340, justify="left",
        ).pack(anchor="w", padx=10, pady=(2, 8))

    # ─────────────────────────────────────────────────────────────────────────
    #  RIGHT — explanation + AI feedback
    # ─────────────────────────────────────────────────────────────────────────
    right = CTkFrame(body, corner_radius=10, fg_color=("#f0f0f0", "#1c1c2e"))
    right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
    right.grid_rowconfigure(2, weight=1)   # reason box expands
    right.grid_columnconfigure(0, weight=1)

    CTkLabel(
        right, text="Explain Your Decision",
        font=CTkFont(size=14, weight="bold"),
    ).grid(row=0, column=0, pady=(10, 2), padx=12, sticky="w")

    CTkLabel(
        right,
        text="Why did you pick this upgrade?\nHow do you plan to use it in battle?",
        font=CTkFont(size=11), text_color="#888888",
        wraplength=380, justify="left",
    ).grid(row=1, column=0, padx=12, pady=(0, 6), sticky="w")

    reason_box = CTkTextbox(
        right, wrap="word",
        fg_color=("#e8e8e8", "#252535"),
    )
    reason_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))

    # AI feedback section
    CTkLabel(
        right, text="AI Feedback",
        font=CTkFont(size=13, weight="bold"),
    ).grid(row=3, column=0, pady=(4, 2), padx=12, sticky="w")

    ai_box = CTkTextbox(
        right, height=115, state="disabled", wrap="word",
        fg_color=("#e0e0e0", "#202030"),
    )
    ai_box.grid(row=4, column=0, sticky="ew", padx=10, pady=(0, 8))

    def _set_ai(text: str):
        ai_box.configure(state="normal")
        ai_box.delete("1.0", "end")
        ai_box.insert("1.0", text)
        ai_box.configure(state="disabled")

    # Submit button
    def on_submit():
        if chosen_idx[0] is None:
            messagebox.showerror(
                "No Upgrade Selected",
                "Please select one of the upgrade options on the left first.",
            )
            return
        reason = reason_box.get("1.0", "end").strip()
        if not reason:
            messagebox.showerror(
                "No Explanation",
                "Please write your reasoning in the text box before submitting.",
            )
            return

        _set_ai("⟳  Evaluating your decision…")
        submit_btn.configure(state="disabled", text="Submitting…")

        def _fetch():
            feedback = call_ai(
                selected_character, selected_card_name,
                selected_epiphany, reason,
            )
            _set_ai(feedback)
            submit_btn.configure(state="normal", text="Submit")

        threading.Thread(target=_fetch, daemon=True).start()

    submit_btn = CTkButton(
        right, text="Submit", width=190, height=40,
        font=CTkFont(size=13, weight="bold"),
        fg_color="#2b5ea0", hover_color="#3a7ad0",
        command=on_submit,
    )
    submit_btn.grid(row=5, column=0, pady=(0, 12))

    # ── Bottom navigation ─────────────────────────────────────────────────────
    nav = CTkFrame(page, fg_color="transparent")
    nav.grid(row=3, column=0, pady=(0, 10))

    CTkButton(
        nav, text="← Back to Cards", width=150,
        fg_color="#555555", hover_color="#333333",
        command=lambda: [page.destroy(), show_window2()],
    ).pack(side="left", padx=10)

    CTkButton(
        nav, text="Start Over", width=130,
        fg_color="#8b1a1a", hover_color="#aa2222",
        command=lambda: [page.destroy(), show_window1()],
    ).pack(side="left", padx=10)


# ═══════════════════════════════════════════════════════════════════════════════
#  Launch
# ═══════════════════════════════════════════════════════════════════════════════
show_window1()
app.mainloop()