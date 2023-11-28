function isSafari() {
  const userAgent = navigator.userAgent.toLowerCase()
  return (
    userAgent.includes("safari") &&
    !userAgent.includes("chrome") &&
    !userAgent.includes("crios") &&
    !userAgent.includes("chromium") &&
    !userAgent.includes("edg")
  )
}

function isPWA() {
  return window.matchMedia("(display-mode: standalone)").matches
}

if (isSafari() && !isPWA()) {
  alert(
    "本作をSafariでプレイする場合、7日の間にサイトを再訪しないとセーブデータが消失します。Chromeなど他のブラウザをお使いいただく、もしくはスマートフォンの場合はPWAとして実行（ホーム画面に追加）いただくことでデータの消失を防ぐことができます。"
  )
}
