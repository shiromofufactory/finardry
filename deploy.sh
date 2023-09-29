pyxel package ./src ./src/main.py
pyxel app2html src.pyxapp
rm -rf public/*
mv src.html public/index.html
OLD="<!DOCTYPE html>"
NEW="<!DOCTYPE html><meta name='viewport' content='width=512' /><link rel='manifest' href='/manifest.json' /><script> if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js')</script>"
OLD_ESCAPED=$(echo "$OLD" | sed 's/[\/&]/\\&/g')
NEW_ESCAPED=$(echo "$NEW" | sed 's/[\/&]/\\&/g')
sed -i '' "s/${OLD_ESCAPED}/${NEW_ESCAPED}/g" public/index.html
cp public/index.html public/nopad.html
OLD="gamepad: \"enabled\""
NEW="gamepad: \"disabled\""
sed -i '' "s/${OLD}/${NEW}/g" public/nopad.html
cp static/* public/
cp -r src/musics public/
cp -r src/data public/
cp -r src/maps public/
rm -f src.pyxapp
firebase deploy --only hosting