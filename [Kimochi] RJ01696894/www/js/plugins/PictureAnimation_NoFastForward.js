//=============================================================================
// PictureAnimation_NoFastForward.js
// ----------------------------------------------------------------------------
// 本プラグインは、トリアコンタン氏作「PictureAnimation.js」の拡張プラグインです。
// PictureAnimation.js: http://triacontane.blogspot.jp/
/*:
 * @plugindesc PictureAnimation拡張
 * @author hami
 *
 */
(function() {
    'use strict';

    // 同一の描画フレーム内では2回目以降の呼び出しをスキップするガード
    var paFrameGuard = function(picture) {
        var frame = Graphics.frameCount;
        if (picture._paNffLastFrame === frame) {
            return false;
        }
        picture._paNffLastFrame = frame;
        return true;
    };

    var _Game_Picture_updateAnimationFrame      = Game_Picture.prototype.updateAnimationFrame;
    Game_Picture.prototype.updateAnimationFrame = function() {
        if (!paFrameGuard(this)) return;
        _Game_Picture_updateAnimationFrame.call(this);
    };

    var _Game_Picture_updateFading      = Game_Picture.prototype.updateFading;
    Game_Picture.prototype.updateFading = function() {
        if (!paFrameGuard(this)) return;
        _Game_Picture_updateFading.call(this);
    };
})();