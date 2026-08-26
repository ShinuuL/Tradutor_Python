/*:ja
 * @plugindesc [基本設定]　放置していると画面がフリーズするのを修正
 * @author kido
 *
 * @help 
 * This core script modification is included.
 * https://github.com/rpgtkoolmv/corescript/pull/191
 * 
 */


(function () {

  var _render = Graphics.render;
  Graphics.render = function (stage) {
    if (this._skipCount < 0) {
      this._skipCount = 0;
    }
    _render.call(this, stage);
  };
})();