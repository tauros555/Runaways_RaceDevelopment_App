# v6.6 Streamlit Cloud fix

## Fixed
1. `st.tabs` removed from main navigation.
   Streamlit tabs execute all tab bodies, so the model was loading even while the Master page was selected.
   v6.6 uses sidebar navigation and executes only the selected page.

2. Current race card no longer uploads in the browser.
   Race prediction reads `data/調教判定表.csv` directly.

3. Google Drive has its own page.
   It can be opened without loading the sklearn race models.

4. Model dependency versions are pinned.

## IMPORTANT: Python version
The bundled `.joblib` models were verified with Python 3.13.
Your failed deployment trace used Python 3.14.

Streamlit Cloud cannot change Python version in-place.
Delete the current app and redeploy it:
- Repository: tauros555/Runaways_RaceDevelopment_App
- Branch: main
- Main file: app.py
- Advanced settings -> Python version: 3.13

Then deploy.

## Google Drive
Google Drive will remain OFF until Streamlit Secrets contains `[gdrive_oauth]`.
This is expected and is separate from the model error.
