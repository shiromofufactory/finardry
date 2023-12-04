functions = require("firebase-functions")
const admin = require("firebase-admin")
admin.initializeApp()
const db = admin.database()

exports.load = functions.https.onRequest(async (req, res) => {
  res.set("Access-Control-Allow-Origin", "*")
  const { id } = req.query
  if (!id) return res.status(400).end()
  const snapshots = await db.ref(id).get()
  res.status(200).send(snapshots.val())
})

exports.save = functions.https.onRequest(async (req, res) => {
  res.set("Access-Control-Allow-Origin", "*")
  const { id, pwd, data } = req.query
  const json = JSON.parse(data)
  const keys = (await db.ref("keys").get()).val() || {}
  let save_code = id
  let password = pwd
  if (!save_code || save_code == "None") {
    do {
      rnd = Math.floor(Math.random() * 1000000)
      save_code = String(rnd).padStart(6, "0")
      if (keys[save_code]) save_code = null
    } while (!save_code)
    password = String(Math.floor(Math.random() * 1000000)).padStart(6, "0")
    keys[save_code] = password
  } else {
    if (keys[save_code] !== pwd) return res.status(400).end()
  }
  await Promise.all([db.ref(save_code).set(json), db.ref("keys").set(keys)])
  res.status(200).send(`${save_code},${password}`)
})
