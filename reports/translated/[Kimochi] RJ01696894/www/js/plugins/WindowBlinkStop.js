//=============================================================================
// WindowBlinkStop.js
// ----------------------------------------------------------------------------
// (C)2017 Triacontane
// This software is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
//  1.0.1 2021/05/30 Fixed an issue where the page-flip animation for message windows and others would stop.
//  1.0.0 2017/12/09 Initial release.
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc WindowBlinkStopPlugin
 * @author triacontane
 *
 * @help WindowBlinkStop.js
 *
 * Stops the blinking of the selected window cursor.
 *
 * This plugin has no plugin commands.
 *
 * This plugin is released under the MIT License.
 */
/*:ja
 * @plugindesc [選択肢]　ウィンドウ点滅停止プラグイン
 * @author トリアコンタン
 *
 * @help WindowBlinkStop.js
 *
 * Stops the blinking of the selected window cursor.
 *
 * This plugin has no plugin commands.
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */

(function() {
    'use strict';

    var _Window__updateCursor = Window.prototype._updateCursor;
    Window.prototype._updateCursor = function() {
        var prevCount = this._animationCount;
        this._animationCount = 0;
        _Window__updateCursor.apply(this, arguments);
        this._animationCount = prevCount;
    };
})();

