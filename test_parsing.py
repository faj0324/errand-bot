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

print("\n" + ("ALL PASS" if not failures else f"{len(failures)} FAILED: {failures}"))
raise SystemExit(1 if failures else 0)
