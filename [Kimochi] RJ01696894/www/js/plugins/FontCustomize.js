/*:
 * @plugindesc [メッセージ]　フォントのカスタマイズ
 * @author hami
 *
 * @param fontSize
 * @text フォントサイズ
 * @desc デフォルトのフォントサイズ
 * @type number
 * @default 28
 *
 * @param fontColor
 * @text フォント色
 * @desc デフォルトのフォント色（CSS形式）
 * @type string
 * @default #ffffff
 *
 * @param lineHeight
 * @text 行の高さ
 * @desc テキストの行の高さ（ピクセル）
 * @type number
 * @default 36
 *
 * @param outlineWidth
 * @text 縁取りの太さ
 * @desc フォントの縁取りの太さ（ピクセル）
 * @type number
 * @default 4
 *
 * @param outlineColor
 * @text 縁取りの色
 * @desc フォントの縁取りの色（CSS形式）
 * @type string
 * @default rgba(0, 0, 0, 1.0)
 *
 * @help
 * 
 */

(function() {
    'use strict';

    const pluginName = 'FontCustomize';
    const parameters = PluginManager.parameters(pluginName);

    // パラメータ取得
    const params = {
        fontSize: Number(parameters['fontSize'] || 28),
        fontColor: String(parameters['fontColor'] || '#ffffff'),
        lineHeight: Number(parameters['lineHeight'] || 36),
        outlineWidth: Number(parameters['outlineWidth'] || 4),
        outlineColor: String(parameters['outlineColor'] || 'rgba(0, 0, 0, 1.0)')
    };

    // ===== フォント設定 =====
    
    // フォントサイズ
    Window_Base.prototype.standardFontSize = function() {
        return params.fontSize;
    };

    // 行の高さ
    Window_Base.prototype.lineHeight = function() {
        return params.lineHeight;
    };

    // フォント色のリセット
    const _Window_Base_resetFontSettings = Window_Base.prototype.resetFontSettings;
    Window_Base.prototype.resetFontSettings = function() {
        _Window_Base_resetFontSettings.call(this);
        this.changeTextColor(params.fontColor);
        this.contents.outlineWidth = params.outlineWidth;
        this.contents.outlineColor = params.outlineColor;
        
    };

})();