// FakePlugin: fixture for extractor step A2 (jp-dense filter).
// Expected candidates when scanned (comments stay ASCII on purpose):
// - technical literal with a single CJK char, no kana (ignored by
//   jp-dense, emitted by mode all);
// - dialogue with kana (kept in both modes);
// - snippet whose only dense signal is the corner brackets
//   (kept in both modes).
(function () {
    PluginManager.registerCommand("FakePlugin", "PA_INIT", function (args) {
        var rate = Number(args.rate || "PA_INIT 6 12 横");
        this._rate = rate;
    });

    Game_Message.prototype.say = function () {
        $gameMessage.add("こいつは話さない");
    };

    Game_Message.prototype.menu = function () {
        $gameMessage.add("「GOLD 討」");
    };
})();
