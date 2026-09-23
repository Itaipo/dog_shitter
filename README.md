# Kora — סביבת פיתוח ראשונית

שלד התוכנה של מכונת החטיפים לקורה. כרגע אין שליטה ברכיבים ואין תלות בחומרה.

## הפעלה במחשב Windows (PowerShell, מתוך תיקיית הפרויקט)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m kora
```

תוצאה צפויה: `Kora development environment is ready (no hardware connected).`

אם `py` אינו מזוהה, נבדוק קודם את התקנת Python לפני שממשיכים.

## Git מקומי

```powershell
git init
git add .
git commit -m "Create Kora development skeleton"
```

מאגר מרוחק פרטי יחובר לאחר בחירת השירות והכתובת. אין להכניס סיסמאות, מפתחות או קובצי `.env` למאגר. הכללים בקובץ `.gitignore` אינם מוחקים סוד שכבר נכנס ל־Git.

## בהמשך על Raspberry Pi

אחרי הכנת המערכת והתחברות SSH: ליצור `.venv` חדש **על ה־Pi**, להתקין את הפרויקט מחדש ולבדוק `python -m kora`. אין להעתיק את `.venv` של Windows. חיבורי מצלמה, קול וסרוו יתווספו אחרי אימות החומרה.

ארבעת מסמכי המקור `PROJECT.md`, `HARDWARE.md`, `TASKS.md`, `DECISIONS.md` נשארים כרגע העותק הרשמי. כאשר מאגר Git יהיה המקור הרשמי, נעביר אותם לתיקיית `docs/` באופן יזום.
