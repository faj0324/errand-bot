"""Parser checks. Run: python test_parsing.py"""

from datetime import datetime

from parsing import categorize, extract_deadline, parse_message

NOW = datetime(2026, 8, 4, 10, 0)  # Tue 4 Aug 2026, 10:00

failures = []


def check(label, got, want):
    ok = got == want
    print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if not ok:
        print(f"        got:  {got!r}\n        want: {want!r}")
        failures.append(label)


print("categorize")
check("milk -> groceries", categorize("milk"), "groceries")
check("2 loaves of bread -> groceries", categorize("2 loaves of bread"), "groceries")
check("prescription -> pharmacy", categorize("pick up my prescription"), "pharmacy")
check("pharmacy -> pharmacy", categorize("go to the pharmacy"), "pharmacy")
check("bank -> errand", categorize("drop cheque at the bank"), "errand")
check("pharmacy beats groceries", categorize("milk and paracetamol"), "pharmacy")

print("\nextract_deadline")
check("before 6pm", extract_deadline("post the parcel before 6pm", NOW)[0],
      datetime(2026, 8, 4, 18, 0))
check("  strips phrase", extract_deadline("post the parcel before 6pm", NOW)[1],
      "post the parcel")
check("tomorrow morning", extract_deadline("call the dentist tomorrow morning", NOW)[0],
      datetime(2026, 8, 5, 9, 0))
check("today -> end of day", extract_deadline("return the book today", NOW)[0],
      datetime(2026, 8, 4, 23, 59))
check("tonight", extract_deadline("wash the car tonight", NOW)[0],
      datetime(2026, 8, 4, 20, 0))
check("no time -> None", extract_deadline("buy milk", NOW)[0], None)
check("  text untouched", extract_deadline("buy milk", NOW)[1], "buy milk")

print("\nparse_message")
items = parse_message("milk, eggs, bread and pick up my prescription before 6pm", NOW)
check("splits into 4", len(items), 4)
check("texts", [i["text"] for i in items],
      ["milk", "eggs", "bread", "pick up my prescription"])
check("categories", [i["category"] for i in items],
      ["groceries", "groceries", "groceries", "pharmacy"])
check("deadline applies to all", {i["deadline"] for i in items},
      {datetime(2026, 8, 4, 18, 0)})

items = parse_message("I need to post a parcel and buy milk tomorrow morning", NOW)
check("filler stripped", items[0]["text"], "post a parcel")
check("2 items", len(items), 2)
check("shared deadline", items[0]["deadline"], datetime(2026, 8, 5, 9, 0))

items = parse_message("buy bread; collect medicine before 5pm", NOW)
check("per-item deadline", items[1]["deadline"], datetime(2026, 8, 4, 17, 0))
check("semicolon split", [i["text"] for i in items], ["buy bread", "collect medicine"])

items = parse_message("call mum", NOW)
check("single item, no deadline", (items[0]["text"], items[0]["deadline"]),
      ("call mum", None))

print("\nregressions from real phone use")
check("'5 pm' spaced", extract_deadline("collect passport before 5 pm", NOW)[0],
      datetime(2026, 8, 4, 17, 0))
check("bare 'before 5' -> 17:00", extract_deadline("collect passport before 5", NOW)[0],
      datetime(2026, 8, 4, 17, 0))
check("bare 'by 9' -> 09:00", extract_deadline("post it by 9", NOW)[0],
      datetime(2026, 8, 5, 9, 0))  # 09:00 today has passed at 10:00, so tomorrow
check("'at 8' -> 08:00 tomorrow", extract_deadline("gym at 8", NOW)[0],
      datetime(2026, 8, 5, 8, 0))
check("'5:30 pm'", extract_deadline("meet at 5:30 pm", NOW)[0],
      datetime(2026, 8, 4, 17, 30))
check("'tomorrow at 5pm' keeps the day",
      extract_deadline("call them tomorrow at 5pm", NOW)[0],
      datetime(2026, 8, 5, 17, 0))
check("'in 2 hours' still works", extract_deadline("leave in 2 hours", NOW)[0],
      datetime(2026, 8, 4, 12, 0))
check("bare number alone is not a time", extract_deadline("buy 6 eggs", NOW)[0], None)

items = parse_message("Milk bread i should collect my passport also before 5 pm", NOW)
check("splits on 'i should'/'also'", [i["text"] for i in items],
      ["Milk", "bread", "collect my passport"])
check("categories after split", [i["category"] for i in items],
      ["groceries", "groceries", "errand"])
check("deadline on all three", {i["deadline"] for i in items},
      {datetime(2026, 8, 4, 17, 0)})
check("keyword run splits", [i["text"] for i in parse_message("milk eggs bread", NOW)],
      ["milk", "eggs", "bread"])
check("ordinary phrase stays whole",
      [i["text"] for i in parse_message("collect my passport", NOW)],
      ["collect my passport"])

print("\n" + ("ALL PASS" if not failures else f"{len(failures)} FAILED: {failures}"))
raise SystemExit(1 if failures else 0)
