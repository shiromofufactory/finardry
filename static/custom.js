function enableItp23() {
  const userAgent = navigator.userAgent.toLowerCase()

  const isSafari =
    userAgent.includes("safari") &&
    !userAgent.includes("chrome") &&
    !userAgent.includes("chromium") &&
    !userAgent.includes("edg")

  const isMacOriOS =
    userAgent.includes("mac os") || userAgent.includes("iphone os")

  return isSafari && isMacOriOS
}

function isPWA() {
  return window.matchMedia("(display-mode: standalone)").matches
}

if (enableItp23() && !isPWA()) {
  alert(
    "本作をこのブラウザでプレイいただく場合、7日以内にサイトを再訪しないとセーブデータが消失する可能性があります。\n\n【データ消失を防ぐ方法】\n・PCの方→Chromeなど他のブラウザをお使いください。\n・スマートフォンの方→PWAとして実行（ホーム画面に追加）してください。"
  )
}
