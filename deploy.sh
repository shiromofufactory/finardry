pyxel package ./src ./src/main.py
pyxel app2html src.pyxapp
rm -rf public/*
mv src.html public/index.html
OLD="<!DOCTYPE html>"
NEW="<!DOCTYPE html><meta charset='UTF-8'><meta property='og:title' content='Finardry' /><meta property='og:description' content='FC時代のウィザードリィをFC時代のFF風のUIにアレンジした二次創作ゲーム。ブラウザでプレイ可能。' /><meta property='og:image' content='https://finardry.web.app/ogp.jpg' /><meta property='og:type' content='website' /><meta name='viewport' content='width=768' /><link rel='manifest' href='/manifest.json' /><script> if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js')</script><script src='/custom.js'></script>"
OLD_ESCAPED=$(echo "$OLD" | sed 's/[\/&]/\\&/g')
NEW_ESCAPED=$(echo "$NEW" | sed 's/[\/&]/\\&/g')
sed -i '' "s/${OLD_ESCAPED}/${NEW_ESCAPED}/g" public/index.html
OLD="https://cdn.jsdelivr.net/gh/kitao/pyxel/wasm/"
NEW="/"
OLD_ESCAPED=$(echo "$OLD" | sed 's/[\/&]/\\&/g')
NEW_ESCAPED=$(echo "$NEW" | sed 's/[\/&]/\\&/g')
sed -i '' "s/${OLD_ESCAPED}/${NEW_ESCAPED}/g" public/index.html
cp public/index.html public/nopad.html
OLD="gamepad: \"enabled\""
NEW="gamepad: \"disabled\""
sed -i '' "s/${OLD}/${NEW}/g" public/nopad.html
cp -r static/* public/
cp -r src/musics public/
cp -r src/data public/
cp -r src/maps public/
mv -f src.pyxapp finardry.pyxapp
firebase deploy --only hosting