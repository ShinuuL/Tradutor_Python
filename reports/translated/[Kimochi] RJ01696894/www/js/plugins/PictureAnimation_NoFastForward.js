//=============================================================================
// PictureAnimation_NoFastForward.js
// ----------------------------------------------------------------------------
// This plugin is an extension of the PictureAnimation.js created by Mr. Triacontan.
// PictureAnimation.js: http://triacontane.blogspot.jp/
/*:
 * @plugindesc PictureAnimation拡張
 * @author hami
 *
 */
(function() {
    'use strict';

    // Skips subsequent calls within the same drawing frame
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