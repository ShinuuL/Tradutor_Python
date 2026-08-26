//=============================================================================
// DTextPicture.js
// ----------------------------------------------------------------------------
// (C) 2015 Triacontane
// This software is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 1.20.5 2023/06/01 Added a note that the "Font Load Plugin" is required for the font change function.
// 1.20.4 2022/06/28 Fixed an issue where the rectangular cursor display in the window did not match the specified parameters.
// 1.20.3 2021/04/29 Fixed an issue where control characters could no longer be used to specify font size in plugin commands.
// 1.20.2 2021/02/09 Modified to exclude control characters of D_TEXT from conversion when used with NRP_EvalPluginCommand.js.
// 1.20.1 2021/02/08 Fixed an issue where picture strings for text with color adjustments were not displayed when the same number was used to create picture strings for text.
// 1.20.0 2020/07/11 Added a feature to specify a prefix text for all picture strings for text.
// 1.19.0 2020/04/09 Added a feature to specify spacing for frame windows.
// 1.18.0 2020/04/05 Added a feature to specify characters that can be filled by control characters \v[n, m] from parameters.
// 1.17.0 2020/02/07 Added a feature to change the skin of the background window and support Window Builder.
// 1.16.0 2020/02/01 Add a feature to specify the line spacing when multiple lines are displayed
// 1.15.1 2019/12/29 Fix a conflict where real-time variable conversion stops working when used with YEP_PluginCmdSwVar.js
// 1.15.0 2019/10/21 Add a command to change the active state of the cursor
//                   Add a setting to change the icon display option using control characters for item display
// 1.14.0 2019/01/13 Add a feature to display a cursor on the background window
// 1.13.0 2018/11/25 Add a feature to set a background color gradient
// 1.12.0 2018/11/08 Change the specification to link the transparency of the background window and the string picture transparency
// 1.11.1 2018/10/20 Fix an issue where variable real-time display works even when passing a string type number as an index to Game_Variables.prototype.setValue (by奏ねこまさん)
// 1.11.0 2018/10/13 Add a feature to apply the settings of the official plugin "TextDecoration.js" to animated text strings
// 1.10.1 2018/05/30 Fix an issue where the outline color is not correctly set when specifying 0 or other strings in the outline color retrieval (by奏ねこまさん)
// 1.10.0 2017/02/12 Added functionality to specify outline color using window color number
// 1.9.0 2017/08/20 Fixed issue where windows were not appearing below overlapping picture windows
// 1.8.6 2017/06/28 Added missing help for the font change function
// 1.8.5 2017/06/12 Fixed issue where zero padding was not correctly displayed for negative values
// 1.8.4 2017/05/10 Fixed issue where text picture was not created the first time when loading data with unapplied plugins
// 1.8.3 2017/04/19 Partial support added for the auto translation plugin
// 1.8.2 2017/04/05 Fixed issue where an error occurred when deleting pictures
// 1.8.1 2017/03/30 Fixed issue where scaling and origin were not supported
// 1.8.0 2017/03/30 Added functionality to display windows on the background
// 1.7.1 2017/03/20 Fixed issue where the italic part was cut off at the end in 1.7.0
// 1.7.0 2017/03/20 Added functionality to make dynamic text strings bold and italic
//                  Fixed an issue where the height was incorrectly calculated when multiple lines were displayed and an icon was specified using control characters
// 1.6.2 2016/12/13 Fixed an issue where images would disappear when displaying and changing the color tone of a picture in the same frame for dynamic pictures
// 1.6.1 2016/11/03 Various conflict countermeasures
// 1.6.0 2016/11/03 Added functionality to use installed fonts as picture fonts
// 1.5.1 2016/10/27 Fixed an issue where specifying an outline color would cause an error in 1.5.0
// 1.5.0 2016/10/23 Added functionality to update the content of variables displayed with control characters in real time
// 1.4.2 2016/07/02 Fixed an issue where control characters would not be reflected when directly executed from a script (though additional escaping is required)
// 1.4.1 2016/06/29 Fixed an issue where text size increased with the control character '\{' would not be displayed at the correct size unless the original size was reset
// 1.4.0 2016/06/28 Changed specification so that images are prioritized when displaying a picture after specifying an image with D_TEXT
// 1.3.1 2016/06/07 Fixed an issue where characters were not drawn when drawing text was limited to half-width alphanumeric characters and no font was specified
// 1.3.0 2016/06/03 Added support for control characters \oc[c] \ow[n]
// 1.2.2 2016/03/28 Added a control character to easily output database information
// 1.2.1 2016/01/29 Corrected an implementation mistake where the command "D_TEXT_SETTING" was implemented as "D_TEST_SETTING" (笑)
// 1.2.0 2016/01/27 Added support for multi-line display
//                  Added a function to set text alignment and background color
//                  Added a function to display variables with leading zeros
// 1.1.3 2015/12/10 Fixed an issue where pictures could be used in the battle screen
//                  Fixed an issue where changes to variables after drawing and opening a debug screen would be reflected in a redraw
// 1.1.2 2015/11/07 Fixed an issue where the program could still run normally even if half-width spaces were included in the drawing string
// 1.1.0 2015/11/07 制御文字\C[n] \I[n] \{ \} に対応（\$と表示スピード制御系以外全部）
// 1.0.1 2015/11/07 Updated comment notation to match RPG Maker MV (Japanese version)
// 1.0.0 2015/11/06 Initial release
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc 動的文字列ピクチャ生成プラグイン
 * @author トリアコンタン
 *
 * @param itemIconSwitchId
 * @text アイテムアイコンスイッチID
 * @desc 指定した番号のスイッチがONのとき\ITEM[n]でアイコンが表示されます。指定しない場合、常に表示されます。
 * @default 0
 * @type switch
 *
 * @param lineSpacingVariableId
 * @text 行間補正変数ID
 * @desc 複数行表示の際の行間に、指定した変数の値の分だけ補正が掛かります。大きすぎる値を設定すると見切れる場合があります。
 * @default 0
 * @type variable
 *
 * @param frameWindowSkin
 * @text フレームウィンドウスキン
 * @desc フレームウィンドウのスキンファイル名です。ウィンドウビルダーを使っている場合は、指定する必要があります。
 * @default
 * @require 1
 * @dir img/system/
 * @type file
 *
 * @param frameWindowPadding
 * @text フレームウィンドウ余白
 * @desc フレームウィンドウの余白です。
 * @default 18
 * @type number
 *
 * @param padCharacter
 * @text 埋め文字
 * @desc 数値描画時、指定桁数に満たないときに埋められる文字です。半角で1文字だけ指定してください。
 * @default 0
 *
 * @param prefixText
 * @text 接頭辞文字列
 * @desc すべての文字列ピクチャの前に挿入されるテキストです。主にデフォルトの制御文字などを指定します。
 * @default
 *
 * @help 指定した文字列でピクチャを動的に生成するコマンドを提供します。
 * Various control characters such as \v[n] can also be used in strings, allowing the content of the picture to be updated in real-time when the value of the variable displayed by control characters changes.
 * The following steps are used for display.
 *
 * 以下の手順で表示します。
 *  1 : プラグインコマンド[D_TEXT]で描画したい文字列と引数を指定（下記の例参照）
 *  2 : プラグインコマンド[D_TEXT_SETTING]で背景色や揃えを指定（任意）
 * * At step 1, the picture will not be displayed, so always call them in pairs.
 *
 * ※ If you execute D_TEXT multiple times before picture display, it will be displayed over multiple lines.
 *
 * ※ Starting from ver1.4.0, after executing [D_TEXT], if you specify "image" in the "picture display" for animated text picture generation,
 *    the behavior has been changed so that it will normally display the "image" picture.
 *   (Separate arguments with a half-width space)
 *
 * Plugin command details
 *   Execute the event command "Plugin Command".
 *
 *
 *  D_TEXT [描画文字列] [文字サイズ] : 動的文字列ピクチャ生成の準備
 *  Example: D_TEXT Test string 32
 *
 * After display, it can be moved, rotated, or deleted just like a regular picture.
 *  It also supports control characters such as variables and actor display.
 *
 *  D_TEXT_SETTING ALIGN [揃え] : 揃え（左揃え、中央揃え、右揃え）の設定
 *  0:Left-justified 1:Centered 2:Right-justified
 *
 *  Example: D_TEXT_SETTING ALIGN 0
 *      D_TEXT_SETTING ALIGN CENTER
 *
 *  Note: The alignment setting will adjust to the widest line when multiple lines are specified.
 *  Therefore, if only a single line is drawn, this setting will not function.
 *
 *  D_TEXT_SETTING BG_COLOR [背景色] : 背景色の設定(CSSの色指定と同様の書式)
 *
 *  Example: D_TEXT_SETTING BG_COLOR black
 *      D_TEXT_SETTING BG_COLOR #336699
 *      D_TEXT_SETTING BG_COLOR rgba(255,255,255,0.5)
 *
 *  You can specify a background color gradient using pixel counts.
 *  D_TEXT_SETTING BG_GRADATION_RIGHT [ピクセル数]
 *  D_TEXT_SETTING BG_GRADATION_LEFT [ピクセル数]
 *
 *  Example: D_TEXT_SETTING BG_GRADATION_RIGHT 50
 *  　　D_TEXT_SETTING BG_GRADATION_LEFT 50
 *
 *  D_TEXT_SETTING REAL_TIME ON : Display variables in real time using control characters
 *
 *  Example: D_TEXT_SETTING REAL_TIME ON
 *
 *  Enabling real-time display ensures that the picture's content will automatically update
 *  when the value of a variable changes after the picture is displayed.
 *
 *  D_TEXT_SETTING WINDOW ON : Display a window on the background
 * Example: D_TEXT_SETTING WINDOW ON
 *
 *  D_TEXT_SETTING FONT [フォント名] : 描画で使用するフォントを指定した名称に変更
 * Example: D_TEXT_SETTING FONT MS Mincho
 *
 * To safely utilize the font change function, you need to use the
 * "Font Load Plugin" that we have publicly released.
 *
 * These settings, like D_TEXT, should be done before displaying the picture.
 *
 * List of supported control characters (same as those in the event command "Display Text")
 * \V[n]
 * \N[n]
 * \P[n]
 * \G
 * \C[n]
 * \I[n]
 * \{
 * \}
 *
 * Dedicated control characters
 * \V[n,m] (Value of the variable filled with m-digit parameters specified)
 * \item[n] n-th item information (icon + name)
 * \weapon[n] n-th weapon information (icon + name)
 * \armor[n] n-th armor information (icon + name)
 * \skill[n] n-th skill information (icon + name)
 * \state[n] n-th state information (icon + name)
 * \oc[c] Set outline color to 'c' (※1)
 * \ow[n] Set outline width to 'n' (example: \ow[5])
 * \f[b] Make font bold
 * \f[i] Make font italic
 * \f[n] Restore font to normal bold and italic
 *
 * ※1 Specify outline color method
 * \oc[red] Specify by color name
 * \oc[rgb(0,255,0)] Specify by color code
 * \oc[2] Specify by character color number similar to \c[n]
 *
 * When a window is displayed as a background, show the cursor.
 * Please execute this command after displaying a moving text string picture.
 *  D_TEXT_WINDOW_CURSOR 1 ON  # Display window cursor on picture[1]
 *  D_TEXT_WINDOW_CURSOR 2 OFF # Remove window cursor from picture[2]
 *
 * The commands to change the cursor's active state are as follows.
 *  D_TEXT_WINDOW_CURSOR_ACTIVE 2 ON  # Activate cursor on picture[1]
 *  D_TEXT_WINDOW_CURSOR_ACTIVE 1 OFF # Stop cursor on picture[1]
 *
 * To specify the coordinates of the cursor rectangle, use the following command.
 *  D_TEXT_WINDOW_CURSOR 1 ON 0 0 100 100  # Display window cursor on picture[1] with size [0,0,100,100]
 *                                         # ウィンドウカーソルを表示
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */
(function() {
    'use strict';

    var getCommandName = function(command) {
        return (command || '').toUpperCase();
    };

    var getArgNumber = function(arg, min, max) {
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        return (parseInt(convertEscapeCharacters(arg.toString())) || 0).clamp(min, max);
    };

    var getArgString = function(arg, upperFlg) {
        arg = convertEscapeCharacters(arg);
        return upperFlg ? arg.toUpperCase() : arg;
    };

    var getArgBoolean = function(arg) {
        return (arg || '').toUpperCase() === 'ON';
    };

    var connectArgs = function(args, startIndex, endIndex) {
        if (arguments.length < 2) startIndex = 0;
        if (arguments.length < 3) endIndex = args.length;
        var text = '';
        for (var i = startIndex; i < endIndex; i++) {
            text += args[i];
            if (i < endIndex - 1) text += ' ';
        }
        return text;
    };

    var convertEscapeCharacters = function(text) {
        if (text === undefined || text === null) text = '';
        var window = SceneManager.getHiddenWindow();
        return window ? window.convertEscapeCharacters(text) : text;
    };

    var getUsingVariables = function(text) {
        var usingVariables = [];

        text = text.replace(/\\/g, '\x1b');
        text = text.replace(/\x1b\x1b/g, '\\');
        text = text.replace(/\x1bV\[(\d+),\s*(\d+)]/gi, function() {
            var number = parseInt(arguments[1], 10);
            usingVariables.push(number);
            return $gameVariables.value(number);
        }.bind(this));
        text = text.replace(/\x1bV\[(\d+)]/gi, function() {
            var number = parseInt(arguments[1], 10);
            usingVariables.push(number);
            return $gameVariables.value(number);
        }.bind(this));
        text = text.replace(/\x1bV\[(\d+)]/gi, function() {
            var number = parseInt(arguments[1], 10);
            usingVariables.push(number);
            return $gameVariables.value(number);
        }.bind(this));
        return usingVariables;
    };

    /**
     * Create plugin parameter. param[paramName] ex. param.commandPrefix
     * @param pluginName plugin name(EncounterSwitchConditions)
     * @returns {Object} Created parameter
     */
    var createPluginParameter = function(pluginName) {
        var paramReplacer = function(key, value) {
            if (value === 'null') {
                return value;
            }
            if (value[0] === '"' && value[value.length - 1] === '"') {
                return value;
            }
            try {
                return JSON.parse(value);
            } catch (e) {
                return value;
            }
        };
        var parameter     = JSON.parse(JSON.stringify(PluginManager.parameters(pluginName), paramReplacer));
        PluginManager.setParameters(pluginName, parameter);
        return parameter;
    };
    var textDecParam          = createPluginParameter('TextDecoration');
    var param                 = createPluginParameter('DTextPicture');

    //=============================================================================
    // Game_Interpreter
    //  Define the plugin command [D_TEXT].
    //=============================================================================
    if ('NRP_EvalPluginCommand'.toLowerCase() in PluginManager._parameters) {
        var _Game_Interpreter_command356 = Game_Interpreter.prototype.command356;
        Game_Interpreter.prototype.command356 = function() {
            this._argClone = this._params[0].split(" ");
            this._argClone.shift();
            return _Game_Interpreter_command356.apply(this, arguments);
        };
    }

    var _Game_Interpreter_pluginCommand      = Game_Interpreter.prototype.pluginCommand;
    Game_Interpreter.prototype.pluginCommand = function(command, args) {
        _Game_Interpreter_pluginCommand.apply(this, arguments);
        if (this._argClone) {
            args = this._argClone;
            this._argClone = null;
        }
        this.pluginCommandDTextPicture(command, args);
    };

    // Resolve conflict for YEP_PluginCmdSwVar.js
    var _Game_Interpreter_processPluginCommandSwitchVariables = Game_Interpreter.prototype.processPluginCommandSwitchVariables;
    Game_Interpreter.prototype.processPluginCommandSwitchVariables = function() {
        if (this._params[0].toUpperCase().indexOf('D_TEXT') >= 0) {
            return;
        }
        _Game_Interpreter_processPluginCommandSwitchVariables.apply(this, arguments);
    };

    Game_Interpreter.textAlignMapper = {
        LEFT: 0, CENTER: 1, RIGHT: 2, Left: 0, Center: 1, Right: 2
    };

    Game_Interpreter.prototype.pluginCommandDTextPicture = function(command, args) {
        switch (getCommandName(command)) {
            case 'D_TEXT' :
                if (isNaN(convertEscapeCharacters(args[args.length - 1])) || args.length === 1) {
                    args.push($gameScreen.dTextSize || 28);
                }
                var fontSize = getArgNumber(args.pop());
                $gameScreen.setDTextPicture(connectArgs(args), fontSize);
                break;
            case 'D_TEXT_SETTING':
                switch (getCommandName(args[0])) {
                    case 'ALIGN' :
                        $gameScreen.dTextAlign = isNaN(args[1]) ?
                            Game_Interpreter.textAlignMapper[getArgString(args[1], true)] : getArgNumber(args[1], 0, 2);
                        break;
                    case 'BG_COLOR' :
                        $gameScreen.dTextBackColor = getArgString(connectArgs(args, 1));
                        break;
                    case 'BG_GRADATION_LEFT' :
                        $gameScreen.dTextGradationLeft = getArgNumber(args[1], 0);
                        break;
                    case 'BG_GRADATION_RIGHT' :
                        $gameScreen.dTextGradationRight = getArgNumber(args[1], 0);
                        break;
                    case 'FONT':
                        args.shift();
                        $gameScreen.setDtextFont(getArgString(connectArgs(args)));
                        break;
                    case 'REAL_TIME' :
                        $gameScreen.dTextRealTime = getArgBoolean(args[1]);
                        break;
                    case 'WINDOW':
                        $gameScreen.dWindowFrame = getArgBoolean(args[1]);
                        break;
                }
                break;
            case 'D_TEXT_WINDOW_CURSOR' :
                var windowRect = null;
                if (getArgBoolean(args[1])) {
                    windowRect = {
                        x     : getArgNumber(args[2] || '', 0),
                        y     : getArgNumber(args[3] || '', 0),
                        width : getArgNumber(args[4] || '', 0),
                        height: getArgNumber(args[5] || '', 0)
                    };
                }
                $gameScreen.setDTextWindowCursor(getArgNumber(args[0], 0), windowRect);
                break;
            case 'D_TEXT_WINDOW_CURSOR_ACTIVE' :
                $gameScreen.setDTextWindowCursorActive(getArgNumber(args[0], 0), getArgBoolean(args[1]));
                break;
        }
    };

    //=============================================================================
    // Game_Variables
    //  Retrieves the history of variables that have been changed.
    //=============================================================================
    var _Game_Variables_setValue      = Game_Variables.prototype.setValue;
    Game_Variables.prototype.setValue = function(variableId, value) {
        variableId = parseInt(variableId);
        if (this.value(variableId) !== value) {
            this._changedVariables = this.getChangedVariables();
            if (!this._changedVariables.contains(variableId)) {
                this._changedVariables.push(variableId);
            }
        }
        _Game_Variables_setValue.apply(this, arguments);
    };

    Game_Variables.prototype.getChangedVariables = function() {
        return this._changedVariables || [];
    };

    Game_Variables.prototype.clearChangedVariables = function() {
        return this._changedVariables = [];
    };

    //=============================================================================
    // Game_Screen
    //  Adds and defines properties for dynamic pictures.
    //=============================================================================
    var _Game_Screen_clear      = Game_Screen.prototype.clear;
    Game_Screen.prototype.clear = function() {
        _Game_Screen_clear.call(this);
        this.clearDTextPicture();
    };

    Game_Screen.prototype.clearDTextPicture = function() {
        this.dTextValue          = null;
        this.dTextOriginal       = null;
        this.dTextRealTime       = null;
        this.dTextSize           = 0;
        this.dTextAlign          = 0;
        this.dTextBackColor      = null;
        this.dTextFont           = null;
        this.dUsingVariables     = null;
        this.dWindowFrame        = null;
        this.dTextGradationRight = 0;
        this.dTextGradationLeft  = 0;
    };

    Game_Screen.prototype.setDTextPicture = function(value, size) {
        if (typeof TranslationManager !== 'undefined') {
            TranslationManager.translateIfNeed(value, function(translatedText) {
                value = translatedText;
            });
        }
        this.dUsingVariables = (this.dUsingVariables || []).concat(getUsingVariables(value));
        this.dTextValue      = (this.dTextValue || '') + getArgString(value, false) + '\n';
        this.dTextOriginal   = (this.dTextOriginal || '') + value + '\n';
        this.dTextSize       = size;
    };

    Game_Screen.prototype.setDTextWindowCursor = function(pictureId, rect) {
        var picture = this.picture(pictureId);
        if (picture) {
            picture.setWindowCursor(rect);
            picture.setWindowCursorActive(true);
        }
    };

    Game_Screen.prototype.setDTextWindowCursorActive = function(pictureId, value) {
        var picture = this.picture(pictureId);
        if (picture) {
            picture.setWindowCursorActive(value);
        }
    };

    Game_Screen.prototype.getDTextPictureInfo = function() {
        var prefix = getArgString(param.prefixText) || '';
        return {
            value         : prefix + this.dTextValue,
            size          : this.dTextSize || 0,
            align         : this.dTextAlign || 0,
            color         : this.dTextBackColor,
            font          : this.dTextFont,
            usingVariables: this.dUsingVariables,
            realTime      : this.dTextRealTime,
            originalValue : prefix + this.dTextOriginal,
            windowFrame   : this.dWindowFrame,
            gradationLeft : this.dTextGradationLeft,
            gradationRight: this.dTextGradationRight,
        };
    };

    Game_Screen.prototype.isSettingDText = function() {
        return !!this.dTextValue;
    };

    Game_Screen.prototype.setDtextFont = function(name) {
        this.dTextFont = name;
    };

    var _Game_Screen_updatePictures      = Game_Screen.prototype.updatePictures;
    Game_Screen.prototype.updatePictures = function() {
        _Game_Screen_updatePictures.apply(this, arguments);
        $gameVariables.clearChangedVariables();
    };

    //=============================================================================
    // Game_Picture
    //  Adds and defines properties for dynamic pictures and modifies the rendering process to be compatible with dynamic pictures.
    //=============================================================================
    var _Game_Picture_initBasic      = Game_Picture.prototype.initBasic;
    Game_Picture.prototype.initBasic = function() {
        _Game_Picture_initBasic.call(this);
        this.dTextValue = null;
        this.dTextInfo  = null;
    };

    var _Game_Picture_show      = Game_Picture.prototype.show;
    Game_Picture.prototype.show = function(name, origin, x, y, scaleX,
                                           scaleY, opacity, blendMode) {
        if ($gameScreen.isSettingDText() && !name) {
            arguments[0]   = Date.now().toString();
            this.dTextInfo = $gameScreen.getDTextPictureInfo();
            $gameScreen.clearDTextPicture();
        } else {
            this.dTextInfo = null;
        }
        _Game_Picture_show.apply(this, arguments);
    };

    var _Game_Picture_update      = Game_Picture.prototype.update;
    Game_Picture.prototype.update = function() {
        _Game_Picture_update.apply(this, arguments);
        if (this.dTextInfo && this.dTextInfo.realTime) {
            this.updateDTextVariable();
        }
    };

    Game_Picture.prototype.updateDTextVariable = function() {
        $gameVariables.getChangedVariables().forEach(function(variableId) {
            if (this.dTextInfo.usingVariables.contains(variableId)) {
                this._name           = Date.now().toString();
                this.dTextInfo.value = getArgString(this.dTextInfo.originalValue, false);
            }
        }, this);
    };

    Game_Picture.prototype.setWindowCursor = function(rect) {
        this._windowCursor = rect;
    };

    Game_Picture.prototype.getWindowCursor = function() {
        return this._windowCursor;
    };

    Game_Picture.prototype.setWindowCursorActive = function(value) {
        this._windowCursorActive = value;
    };

    Game_Picture.prototype.getWindowCursorActive = function() {
        return this._windowCursorActive;
    };

    //=============================================================================
    // SceneManager
    //  Obtains a hidden window for drawing text.
    //=============================================================================
    SceneManager.getHiddenWindow = function() {
        if (!this._hiddenWindow) {
            this._hiddenWindow = new Window_Hidden(1, 1, 1, 1);
        }
        return this._hiddenWindow;
    };

    SceneManager.getSpriteset = function() {
        return this._scene._spriteset;
    };

    //=============================================================================
    // Window_Base
    //  Sets additional control characters for string conversion processing.
    //=============================================================================
    var _Window_Base_convertEscapeCharacters      = Window_Base.prototype.convertEscapeCharacters;
    Window_Base.prototype.convertEscapeCharacters = function(text) {
        text = _Window_Base_convertEscapeCharacters.call(this, text);
        text = text.replace(/\x1bV\[(\d+),\s*(\d+)]/gi, function() {
            return this.getVariablePadCharacter($gameVariables.value(parseInt(arguments[1], 10)), arguments[2]);
        }.bind(this));
        text = text.replace(/\x1bITEM\[(\d+)]/gi, function() {
            var item = $dataItems[getArgNumber(arguments[1], 1, $dataItems.length)];
            return this.getItemInfoText(item);
        }.bind(this));
        text = text.replace(/\x1bWEAPON\[(\d+)]/gi, function() {
            var item = $dataWeapons[getArgNumber(arguments[1], 1, $dataWeapons.length)];
            return this.getItemInfoText(item);
        }.bind(this));
        text = text.replace(/\x1bARMOR\[(\d+)]/gi, function() {
            var item = $dataArmors[getArgNumber(arguments[1], 1, $dataArmors.length)];
            return this.getItemInfoText(item);
        }.bind(this));
        text = text.replace(/\x1bSKILL\[(\d+)]/gi, function() {
            var item = $dataSkills[getArgNumber(arguments[1], 1, $dataSkills.length)];
            return this.getItemInfoText(item);
        }.bind(this));
        text = text.replace(/\x1bSTATE\[(\d+)]/gi, function() {
            var item = $dataStates[getArgNumber(arguments[1], 1, $dataStates.length)];
            return this.getItemInfoText(item);
        }.bind(this));
        return text;
    };

    Window_Base.prototype.getItemInfoText = function(item) {
        if (!item) {
            return '';
        }
        return (this.isValidDTextIconSwitch() ? '\x1bi[' + item.iconIndex + ']' : '') + item.name;
    };

    Window_Base.prototype.isValidDTextIconSwitch = function() {
        return !param.itemIconSwitchId || $gameSwitches.value(param.itemIconSwitchId);
    };

    Window_Base.prototype.getVariablePadCharacter = function(value, digit) {
        var numText = String(Math.abs(value));
        var pad = String(param.padCharacter) || '0';
        while (numText.length < digit) {
            numText = pad + numText;
        }
        return (value < 0 ? '-' : '') + numText;
    };

    //=============================================================================
    // Sprite_Picture
    //  Adds and defines dynamic image generation.
    //=============================================================================
    var _Sprite_Picture_update      = Sprite_Picture.prototype.update;
    Sprite_Picture.prototype.update = function() {
        _Sprite_Picture_update.apply(this, arguments);
        if (this._frameWindow) {
            this.updateFrameWindow();
        }
    };

    Sprite_Picture.prototype.updateFrameWindow = function() {
        var padding               = this._frameWindow.standardPadding();
        this._frameWindow.x       = this.x - (this.anchor.x * this.width * this.scale.x) - padding;
        this._frameWindow.y       = this.y - (this.anchor.y * this.height * this.scale.y) - padding;
        this._frameWindow.opacity = this.opacity;
        if (!this.visible) {
            this.removeFrameWindow();
            return;
        }
        if (!this._addFrameWindow) {
            this.addFrameWindow();
        }
        if (Graphics.frameCount % 2 === 0) {
            this.adjustScaleFrameWindow();
        }
        this.updateFrameWindowCursor();
    };

    Sprite_Picture.prototype.updateFrameWindowCursor = function() {
        var picture = this.picture();
        if (!picture) {
            return;
        }
        var rect = picture.getWindowCursor();
        if (rect) {
            var width  = rect.width || this._frameWindow.contentsWidth();
            var height = rect.height || this._frameWindow.contentsHeight();
            this._frameWindow.setCursorRect(rect.x || 0, rect.y || 0, width, height);
            this._frameWindow.active = picture.getWindowCursorActive();
        } else {
            this._frameWindow.setCursorRect(0, 0, 0, 0);
        }
    };

    Sprite_Picture.prototype.adjustScaleFrameWindow = function() {
        var padding        = this._frameWindow.standardPadding();
        var newFrameWidth  = Math.floor(this.width * this.scale.x + padding * 2);
        var newFrameHeight = Math.floor(this.height * this.scale.x + padding * 2);
        if (this._frameWindow.width !== newFrameWidth || this._frameWindow.height !== newFrameHeight) {
            this._frameWindow.move(this._frameWindow.x, this._frameWindow.y, newFrameWidth, newFrameHeight);
        }
    };

    Sprite_Picture.prototype.addFrameWindow = function() {
        var parent = this.parent;
        if (parent) {
            var index = parent.getChildIndex(this);
            parent.addChildAt(this._frameWindow, index);
            this._addFrameWindow = true;
        }
    };

    Sprite_Picture.prototype.removeFrameWindow = function() {
        var parent = this.parent;
        if (parent) {
            parent.removeChild(this._frameWindow);
            this._frameWindow    = null;
            this._addFrameWindow = false;
        }
    };

    var _Sprite_Picture_loadBitmap      = Sprite_Picture.prototype.loadBitmap;
    Sprite_Picture.prototype.loadBitmap = function() {
        this.dTextInfo = this.picture().dTextInfo;
        if (this.dTextInfo) {
            this.makeDynamicBitmap();
        } else {
            _Sprite_Picture_loadBitmap.apply(this, arguments);
        }
    };

    Sprite_Picture.prototype.makeDynamicBitmap = function() {
        this.textWidths   = [];
        this.hiddenWindow = SceneManager.getHiddenWindow();
        this.hiddenWindow.resetFontSettings(this.dTextInfo);
        var bitmapVirtual = new Bitmap_Virtual();
        this._processText(bitmapVirtual);
        this.hiddenWindow.resetFontSettings(this.dTextInfo);
        this.bitmap = new Bitmap(bitmapVirtual.width, bitmapVirtual.height);
        this.applyTextDecoration();
        this.bitmap.fontFace = this.hiddenWindow.contents.fontFace;
        if (this.dTextInfo.color) {
            this.bitmap.fillAll(this.dTextInfo.color);
            var h             = this.bitmap.height;
            var w             = this.bitmap.width;
            var gradationLeft = this.dTextInfo.gradationLeft;
            if (gradationLeft > 0) {
                this.bitmap.clearRect(0, 0, gradationLeft, h);
                this.bitmap.gradientFillRect(0, 0, gradationLeft, h, 'rgba(0, 0, 0, 0)', this.dTextInfo.color, false);
            }
            var gradationRight = this.dTextInfo.gradationRight;
            if (gradationRight > 0) {
                this.bitmap.clearRect(w - gradationRight, 0, gradationRight, h);
                this.bitmap.gradientFillRect(w - gradationRight, 0, gradationRight, h, this.dTextInfo.color, 'rgba(0, 0, 0, 0)', false);
            }
        }
        this._processText(this.bitmap);
        this.setColorTone([0, 0, 0, 0]);
        if (this._frameWindow) {
            this.removeFrameWindow();
        }
        if (this.dTextInfo.windowFrame) {
            var scaleX = this.picture().scaleX() / 100;
            var scaleY = this.picture().scaleY() / 100;
            this.makeFrameWindow(bitmapVirtual.width * scaleX, bitmapVirtual.height * scaleY);
        }
        this.hiddenWindow = null;
    };

    Sprite_Picture.prototype.applyTextDecoration = function() {
        if (textDecParam.Mode >= 0) {
            this.bitmap.outlineColor   =
                'rgba(%1,%2,%3,%4)'.format(textDecParam.Red, textDecParam.Green, textDecParam.Blue, textDecParam.Alpha / 255);
            this.bitmap.decorationMode = textDecParam.Mode;
        }
    };

    Sprite_Picture.prototype.makeFrameWindow = function(width, height) {
        var padding       = this.hiddenWindow.standardPadding();
        this._frameWindow = new Window_BackFrame(0, 0, width + padding * 2, height + padding * 2);
        if (param.frameWindowSkin) {
            this._frameWindow.windowskin = ImageManager.loadSystem(param.frameWindowSkin);
        }
    };

    Sprite_Picture.prototype._processText = function(bitmap) {
        var textState = {index: 0, x: 0, y: 0, text: this.dTextInfo.value, left: 0, line: -1, height: 0};
        this._processNewLine(textState, bitmap);
        textState.height = this.hiddenWindow.calcTextHeight(textState, false);
        textState.index  = 0;
        while (textState.text[textState.index]) {
            this._processCharacter(textState, bitmap);
        }
    };

    Sprite_Picture.prototype._processCharacter = function(textState, bitmap) {
        if (textState.text[textState.index] === '\x1b') {
            var code = this.hiddenWindow.obtainEscapeCode(textState);
            switch (code) {
                case 'C':
                    bitmap.textColor = this.hiddenWindow.textColor(this.hiddenWindow.obtainEscapeParam(textState));
                    break;
                case 'I':
                    this._processDrawIcon(this.hiddenWindow.obtainEscapeParam(textState), textState, bitmap);
                    break;
                case '{':
                    this.hiddenWindow.makeFontBigger();
                    break;
                case '}':
                    this.hiddenWindow.makeFontSmaller();
                    break;
                case 'F':
                    switch (this.hiddenWindow.obtainEscapeParamString(textState).toUpperCase()) {
                        case 'I':
                            bitmap.fontItalic = true;
                            break;
                        case 'B':
                            bitmap.fontBoldFotDtext = true;
                            break;
                        case '/':
                        case 'N':
                            bitmap.fontItalic       = false;
                            bitmap.fontBoldFotDtext = false;
                            break;
                    }
                    break;
                case 'OC':
                    var colorCode  = this.hiddenWindow.obtainEscapeParamString(textState);
                    var colorIndex = Number(colorCode);
                    if (!isNaN(colorIndex)) {
                        bitmap.outlineColor = this.hiddenWindow.textColor(colorIndex);
                    } else {
                        bitmap.outlineColor = colorCode;
                    }
                    break;
                case 'OW':
                    bitmap.outlineWidth = this.hiddenWindow.obtainEscapeParam(textState);
                    break;
            }
        } else if (textState.text[textState.index] === '\n') {
            this._processNewLine(textState, bitmap);
        } else {
            var c = textState.text[textState.index++];
            var w = this.hiddenWindow.textWidth(c);

            bitmap.fontSize = this.hiddenWindow.contents.fontSize;
            bitmap.drawText(c, textState.x, textState.y, w * 2, textState.height, 'left');
            textState.x += w;
        }
    };

    Sprite_Picture.prototype._processNewLine = function(textState, bitmap) {
        if (bitmap instanceof Bitmap_Virtual)
            this.textWidths[textState.line] = textState.x;
        this.hiddenWindow.processNewLine(textState);
        textState.line++;
        if (bitmap instanceof Bitmap)
            textState.x = (bitmap.width - this.textWidths[textState.line]) / 2 * this.dTextInfo.align;
    };

    Sprite_Picture.prototype._processDrawIcon = function(iconIndex, textState, bitmap) {
        var iconBitmap = ImageManager.loadSystem('IconSet');
        var pw         = Window_Base._iconWidth;
        var ph         = Window_Base._iconHeight;
        var sx         = iconIndex % 16 * pw;
        var sy         = Math.floor(iconIndex / 16) * ph;
        bitmap.blt(iconBitmap, sx, sy, pw, ph, textState.x + 2, textState.y + (textState.height - ph) / 2);
        textState.x += Window_Base._iconWidth + 4;
    };

    //=============================================================================
    // Bitmap_Virtual
    //  Virtual bitmap class for calculating size.
    //=============================================================================
    function Bitmap_Virtual() {
        this.initialize.apply(this, arguments);
    }

    Bitmap_Virtual.prototype.initialize = function() {
        this.window = SceneManager.getHiddenWindow();
        this.width  = 0;
        this.height = 0;
    };

    Bitmap_Virtual.prototype.drawText = function(text, x, y) {
        var baseWidth = this.window.textWidth(text);
        var fontSize  = this.window.contents.fontSize;
        if (this.fontItalic) {
            baseWidth += Math.floor(fontSize / 6);
        }
        if (this.fontBoldFotDtext) {
            baseWidth += 2;
        }
        this.width  = Math.max(x + baseWidth, this.width);
        this.height = Math.max(y + fontSize + 8, this.height);
    };

    Bitmap_Virtual.prototype.blt = function(source, sx, sy, sw, sh, dx, dy, dw, dh) {
        this.width  = Math.max(dx + (dw || sw), this.width);
        this.height = Math.max(dy + (dh || sh), this.height);
    };

    //=============================================================================
    // Window_BackFrame
    //  Back frame window.
    //=============================================================================
    function Window_BackFrame() {
        this.initialize.apply(this, arguments);
    }

    Window_BackFrame.prototype.backOpacity = null;

    Window_BackFrame.prototype             = Object.create(Window_Base.prototype);
    Window_BackFrame.prototype.constructor = Window_BackFrame;

    Window_BackFrame.prototype.standardPadding = function() {
        return param.frameWindowPadding;
    };


    //=============================================================================
    // Window_Hidden
    //  Hidden window for drawing text.
    //=============================================================================
    function Window_Hidden() {
        this.initialize.apply(this, arguments);
    }

    Window_Hidden.prototype.backOpacity = null;

    Window_Hidden.prototype             = Object.create(Window_Base.prototype);
    Window_Hidden.prototype.constructor = Window_Hidden;

    Window_Hidden.prototype._createAllParts = function() {
        this._windowBackSprite      = {};
        this._windowSpriteContainer = {};
        this._windowContentsSprite  = new Sprite();
        this.addChild(this._windowContentsSprite);
    };

    Window_Hidden.prototype._refreshAllParts = function() {};

    Window_Hidden.prototype._refreshBack = function() {};

    Window_Hidden.prototype._refreshFrame = function() {};

    Window_Hidden.prototype._refreshCursor = function() {};

    Window_Hidden.prototype._refreshArrows = function() {};

    Window_Hidden.prototype._refreshPauseSign = function() {};

    Window_Hidden.prototype.updateTransform = function() {};

    Window_Hidden.prototype.resetFontSettings = function(dTextInfo) {
        if (dTextInfo) {
            var customFont         = dTextInfo.font ? dTextInfo.font + ',' : '';
            this.contents.fontFace = customFont + this.standardFontFace();
            this.contents.fontSize = dTextInfo.size || this.standardFontSize();
        } else {
            Window_Base.prototype.resetFontSettings.apply(this, arguments);
        }
    };

    Window_Hidden.prototype.obtainEscapeParamString = function(textState) {
        var arr = /^\[.+?]/.exec(textState.text.slice(textState.index));
        if (arr) {
            textState.index += arr[0].length;
            return arr[0].substring(1, arr[0].length - 1);
        } else {
            return '';
        }
    };

    var _Window_Hidden_calcTextHeight = Window_Hidden.prototype.calcTextHeight;
    Window_Hidden.prototype.calcTextHeight = function(textState, all) {
        var result = _Window_Hidden_calcTextHeight.apply(this, arguments);
        if (param.lineSpacingVariableId) {
            result += $gameVariables.value(param.lineSpacingVariableId);
        }
        return result;
    };

    //=============================================================================
    // Bitmap
    //  Supports bold characters.
    //=============================================================================
    var _Bitmap__makeFontNameText      = Bitmap.prototype._makeFontNameText;
    Bitmap.prototype._makeFontNameText = function() {
        return (this.fontBoldFotDtext ? 'bold ' : '') + _Bitmap__makeFontNameText.apply(this, arguments);
    };
})();
