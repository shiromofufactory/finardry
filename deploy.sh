pyxel package ./src ./src/main.py
pyxel app2html src.pyxapp
rm -rf public/*
mv src.html public/index.html
cp static/* public/
cp -r src/musics public/
cp -r src/data public/
cp -r src/maps public/
rm -f src.pyxapp
firebase deploy --only hosting