//=============================================================================
// NRP_GameWindowSize.js
//=============================================================================
/*:
 * @target MV MZ
 * @plugindesc v1.051 Resize the entire game window & add to the options.
 * @author Takeshi Sunagawa (http://newrpg.seesaa.net/)
 * @orderBefore StartUpFullScreen
 * @url http://newrpg.seesaa.net/article/475413177.html
 *
 * @help Change the window size of the entire game.
 * It also adds the ability to change the window size to the options screen.
 * 
 * ◆Main features
 * - Window size can be set independently from resolution.
 * - Window size change function can be added to the options screen.
 *   If changed, the change will be reflected at startup thereafter.
 * 
 * Note that it does not make sense on mobile or browser activation.
 * This plugin is automatically disabled.
 * 
 * -------------------------------------------------------------------
 * [Notice (for MZ)]
 * -------------------------------------------------------------------
 * ◆About the window size immediately after starting the game
 * The window size at the moment the game is launched
 * cannot be changed by this plugin.
 * Normally, the window size should switch after a beat.
 * 
 * In MZ, the window size immediately after startup is determined
 * by the "Screen Width" and "Screen Height" in "System 2".
 * These are values shared with the pixel size handled in the game.
 * 
 * ※It is somewhat odd that pixel size and window size are determined
 *   by the same item, but there is currently no way around this.
 * 
 * There is no perfect solution, but the following is a tentative one.
 * 
 * If you set the "screenWidth" and "screenHeight" in the plugin parameters,
 * you can change only the pixel size of the game,
 * independently of the "System 2" setting values.
 * In this case, set the window size to the "System 2" setting value.
 * 
 * However, since the System 2 configuration values are also referenced
 * in the editor, the display area of the Troop screen in the database
 * is reduced as a side effect.
 * This is not a problem if the Troop screen is not used
 * at the end of development or in ARPGs.
 * 
 * In addition, the horizontal scroll bar may appear
 * when the screen size is reduced, but this can be suppressed
 * by adding the following three lines to "[Project]\css\game.css"
 * 
 * body::-webkit-scrollbar {
 *    display:none;
 * }
 * 
 * ※Please note that game.css is a file
 *   that may be overwritten when the main unit is upgraded.
 * 
 * -------------------------------------------------------------------
 * [Notice (for MV)]
 * -------------------------------------------------------------------
 * ◆About the window size immediately after starting the game
 * In MV, the window size at the moment of startup can be set
 * in "package.json" directly under the project.
 * If you want to change the standard window size,
 * it is better to set this value as well.
 * This can suppress the behavior of the window size
 * switching immediately after startup.
 * 
 * ◆Conflict with YEP_CoreEngine.
 * YEP_CoreEngine has a specification
 * that forces the window size to match the resolution.
 * By placing this plugin underneath the YEP_CoreEngine,
 * you can only resize the window appropriately.
 * 
 * -------------------------------------------------------------------
 * [Terms]
 * -------------------------------------------------------------------
 * There are no restrictions.
 * Modification, redistribution freedom, commercial availability,
 * and rights indication are also optional.
 * The author is not responsible,
 * but will deal with defects to the extent possible.
 * 
 * @------------------------------------------------------------------
 * @ [Plugin Parameters]
 * @------------------------------------------------------------------
 * @param windowWidth
 * @type string
 * @default Graphics.width
 * @desc The width of the window (exclude frame) as the standard.
 * The default value is the same as the resolution.
 * 
 * @param windowHeight
 * @type string
 * @default Graphics.height
 * @desc The height of the window (exclude frame) as the standard.
 * The default value is the same as the resolution.
 * 
 * @param screenWidth
 * @type string
 * @desc Screen width.
 * Overrides the value of System2 only when entered.
 * 
 * @param screenHeight
 * @type string
 * @desc Screen height.
 * Overrides the value of System2 only when entered.
 * 
 * @param <option>
 * 
 * @param useOption
 * @parent <option>
 * @type boolean
 * @default true
 * @desc Add the ability to change the window size to the options screen.
 * 
 * @param optionPosition
 * @parent <option>
 * @type number
 * @default 2
 * @desc The position to insert an item into the options screen.
 * The default value is 2, which is under Command Remember.
 * 
 * @param optionName
 * @parent <option>
 * @type string
 * @default Window Size
 * @desc Set the display name on the options screen.
 * 
 * @param optionDispType
 * @parent <option>
 * @type select
 * @option % Style @value percent
 * @option Width*Heigth Style @value size
 * @default percent
 * @desc Set the display type on the options screen.
 * 
 * @param windowSizeMin
 * @parent <option>
 * @type string
 * @default 50
 * @desc The minimum window size that can be changed.
 * The default value is 50(%).
 * 
 * @param windowSizeMax
 * @parent <option>
 * @type string
 * @default 150
 * @desc The maximum window size that can be changed.
 * The default value is 150(%).
 * 
 * @param windowSizeOffset
 * @parent <option>
 * @type string
 * @default 25
 * @desc The unit of change in window size.
 * The default value is 25(%).
 * 
 * @param <cooperation>
 * 
 * @param overWriteSceneManagerRun
 * @parent <cooperation>
 * @type boolean
 * @default false
 * @desc Override the SceneManager.run function. This function is used to disable window resizing by YEP_CoreEngine.
 */

/*:ja
 * @target MV MZ
 * @plugindesc v1.051 ゲーム全体のウィンドウサイズを変更＆オプションに追加
 * @author 砂川赳（http://newrpg.seesaa.net/）
 * @orderBefore StartUpFullScreen
 * @url http://newrpg.seesaa.net/article/475413177.html
 *
 * @help ゲーム全体のウィンドウサイズを変更します。
 * Additionally, we will add a window size change function to the option screen.
 * 
 * ◆Main Features
 * • You can set the window size independently of the resolution.
 * • The window size change function can be added to the option screen.
 *  Changes will be reflected upon startup thereafter.
 *
 * Note that this plugin will be automatically disabled in mobile or browser launches,
 * as it would not make sense in those contexts.
 * 
 * -------------------------------------------------------------------
 * ■Note for MZ
 * -------------------------------------------------------------------
 * ◆About the window size immediately after startup
 * The window size at the moment the game is launched cannot be changed by this plugin.
 * It should switch to the new window size with a slight delay, usually one frame.
 * 
 * In MZ, the window size immediately after launch is determined by
 * the "Width" and "Height" settings in System2.
 * These settings decide the pixel size processed within the game and the shared value.
 * 
 * * It's a bit of an odd design that the pixel size and window size are decided in the same setting,
 * but there's not much we can do about it for now.
 * 
 * There is no perfect solution, but here is an interim workaround.
 * 
 * By setting the "Width" and "Height" in the plugin parameters, you can change just the pixel size of the game separately from the System2 settings.
 * This allows you to change the game's pixel size without altering the window size settings in System2.
 * In this case, we will set the window size for System2.
 * 
 * However, since the settings for System2 are also referenced by the editor,
 * as a side effect, the display area of the database enemy group screen will become narrower.
 * This is not a problem if you are not using the enemy group screen in the late development stage or an ARPG.
 * 
 * Additionally, there may be cases where a horizontal scrollbar appears when the screen size is reduced,
 * * Please append the following three lines to [プロジェクト]\css\game.css
 *  to suppress this.
 * 
 * body::-webkit-scrollbar {
 *    display:none;
 * }
 * 
 * * Note that game.css is a file that may be overwritten during the main version update,
 *  so please be cautious.
 * 
 * -------------------------------------------------------------------
 * ■Note Points (For MV)
 * -------------------------------------------------------------------
 * ◆About the window size immediately after startup
 * In the MV, you can set the window size at startup via the `package.json` file located directly under the project.
 * If you want to change the standard window size, it's better to also adjust this value.
 * You can suppress the window size change behavior immediately after startup.
 * The MV has a feature to compete with YEP_CoreEngine regarding window size.
 *
 * Regarding the competition with YEP_CoreEngine:
 * YEP_CoreEngine has a feature to forcibly adjust the window size to the resolution.
 * By placing this plugin below YEP_CoreEngine, you can appropriately change only the window size.
 *
 * 
 * -------------------------------------------------------------------
 * Terms of Use
 * -------------------------------------------------------------------
 * There are no specific restrictions.
 * Changes and redistribution are free, commercial use is allowed, and attribution is optional.
 * The author is not responsible, but will respond within the possible range for issues.
 * 
 * @------------------------------------------------------------------
 * @ Plugin Parameters
 * @------------------------------------------------------------------
 * 
 * @param windowWidth
 * @text ウィンドウ横幅
 * @type string
 * @default Graphics.width
 * @desc 標準とするウィンドウの横幅（枠除く）です。
 * The initial value is the same as the resolution.
 * 
 * @param windowHeight
 * @text ウィンドウ縦幅
 * @type string
 * @default Graphics.height
 * @desc 標準とするウィンドウの縦幅（枠除く）です。
 * The initial value is the same as the resolution.
 * 
 * @param screenWidth
 * @text 画面の幅
 * @type string
 * @desc 画面の横幅です。
 * Only System 2 values will be overwritten during input.
 * 
 * @param screenHeight
 * @text 画面の高さ
 * @type string
 * @desc 画面の縦幅です。
 * Only System 2 values will be overwritten during input.
 * 
 * @param <option>
 * @text ＜オプション＞
 * 
 * @param useOption
 * @text オプションに表示
 * @parent <option>
 * @type boolean
 * @default true
 * @desc ウィンドウサイズの変更機能をオプション画面に追加します。
 * 
 * @param optionPosition
 * @text オプション挿入位置
 * @parent <option>
 * @type number
 * @default 2
 * @desc オプション画面に項目を挿入する位置です。
 * The initial value is 2. Below the command memory.
 * 
 * @param optionName
 * @text オプション表示名
 * @parent <option>
 * @type string
 * @default ウィンドウサイズ
 * @desc オプション画面での表示名を設定します。
 * 
 * @param optionDispType
 * @text オプション表示形式
 * @parent <option>
 * @type select
 * @option ％表示 @value percent
 * @option 横*縦表示 @value size
 * @default percent
 * @desc オプション画面での表示形式を設定します。
 * 
 * @param windowSizeMin
 * @text 最小ウィンドウサイズ
 * @parent <option>
 * @type string
 * @default 50
 * @desc 変更可能な最小のウィンドウサイズです。
 * The initial value is 50(%).
 * 
 * @param windowSizeMax
 * @text 最大ウィンドウサイズ
 * @parent <option>
 * @type string
 * @default 150
 * @desc 変更可能な最大のウィンドウサイズです。
 * The initial value is 150(%).
 * 
 * @param windowSizeOffset
 * @text 変更単位
 * @parent <option>
 * @type string
 * @default 25
 * @desc ウィンドウサイズの変更単位です。
 * The initial value is 25(%).
 * 
 * @param <cooperation>
 * @text ＜外部連携＞
 * 
 * @param overWriteSceneManagerRun
 * @text SceneManager.runを上書
 * @parent <cooperation>
 * @type boolean
 * @default false
 * @desc SceneManager.run関数を上書きします。YEP_CoreEngineのウィンドウサイズ変更を無効化するための機能です。
 */

(function() {
"use strict";

function setDefault(str, def) {
    return str ? str : def;
}
function toNumber(str, def) {
    return isNaN(str) ? def : +(str || def);
}
function toBoolean(str) {
    if (str == true) {
        return true;
    }
    return (str == "true") ? true : false;
}

const parameters = PluginManager.parameters("NRP_GameWindowSize");
// Basic Items
const pWindowWidth = parameters["windowWidth"];
const pWindowHeight = parameters["windowHeight"];
const pScreenWidth = parameters["screenWidth"];
const pScreenHeight = parameters["screenHeight"];
// Options
const pUseOption = toBoolean(parameters["useOption"]);
const pOptionName = parameters["optionName"];
const pOptionPosition = toNumber(parameters["optionPosition"], 2);
const pOptionDispType = parameters["optionDispType"];
const pWindowSizeMin = setDefault(parameters["windowSizeMin"], 50);
const pWindowSizeMax = setDefault(parameters["windowSizeMax"], 150);
const pWindowSizeOffset = setDefault(parameters["windowSizeOffset"], 25);
// External Integration
const pOverWriteSceneManagerRun = toBoolean(parameters["overWriteSceneManagerRun"]);

// Identifier
const WINDOW_SIZE_SYMBOL = "windowSize";

/**
 * Overwrite if exists
 */
if (pOverWriteSceneManagerRun) {
    SceneManager.run = function(sceneClass) {
        try {
            this.initialize();
            this.goto(sceneClass);

            // In the case of MV
            if (Utils.RPGMAKER_NAME == "MV") {
                this.requestUpdate();
            // In the case of MZ
            } else {
                Graphics.startGameLoop();
            }
        } catch (e) {
            this.catchException(e);
        }
    };
}

/**
 * ●Game Launch
 */
const _Scene_Boot_start = Scene_Boot.prototype.start;
Scene_Boot.prototype.start = function() {
    _Scene_Boot_start.apply(this, arguments);

    // Change window size to the set value
    changeWindowSize();

    // Forcefully change screen size
    if (pScreenWidth && pScreenHeight) {
        Graphics.width = eval(pScreenWidth);
        Graphics.height = eval(pScreenHeight);
    }
};

/**
 * ●Change in Window Size
 */
function changeWindowSize() {
    // This feature is disabled except for local execution
    if (!Utils.isNwjs()) {
        return;
    }

    if (pWindowWidth || pWindowHeight) {
        const dw = getWindowWidth() - window.innerWidth;
        const dh = getWindowHeight() - window.innerHeight;
        window.resizeBy(dw, dh);
        window.moveBy(-dw / 2, -dh / 2);
    }
}

/**
 * ●Get window width
 */
function getWindowWidth() {
    var width = Graphics.width;
    if (pWindowWidth) {
        width = eval(pWindowWidth);
    }
    return Math.round(width * getWindowSizeRate());
}

/**
 * ●Get window height
 */
function getWindowHeight() {
    var height = Graphics.height;
    if (pWindowHeight) {
        height = eval(pWindowHeight);
    }
    return Math.round(height * getWindowSizeRate());
}

/**
 * ●Get window size rate
 */
function getWindowSizeRate() {
    var windowSizeRate = 1;
    // If no options are used, set to 1
    if (!pUseOption) {
        return windowSizeRate;
    }

    if (ConfigManager.windowSize) {
        windowSizeRate = ConfigManager.windowSize / 100;
    }

    return windowSizeRate;
}

// This feature is disabled except for local execution
if (!Utils.isNwjs()) {
    return;
}

/**
 * If no options are used, processing ends here
 */
if (!pUseOption) {
    return;
}

/**
 * ●Minimum value for option window size
 */
function windowSizeMin() {
    return eval(pWindowSizeMin);
}

/**
 * ●Maximum value for option window size
 */
function windowSizeMax() {
    return eval(pWindowSizeMax);
}

/**
 * ●Change unit for option window size
 */
function windowSizeOffset() {
    return eval(pWindowSizeOffset);
}

// Initial value for window size
ConfigManager.windowSize = 100;

/**
 * ●Option screen item generation
 */
var _ConfigManager_makeData = ConfigManager.makeData;
ConfigManager.makeData = function() {
    var config = _ConfigManager_makeData.apply(this, arguments);

    config.windowSize = this.windowSize;
    return config;
};

/**
 * ●Option screen item generation
 */
var _ConfigManager_applyData = ConfigManager.applyData;
ConfigManager.applyData = function(config) {
    _ConfigManager_applyData.apply(this, arguments);

    this.windowSize = this.readWindowSize(config, WINDOW_SIZE_SYMBOL);
};

/**
 * 【Custom】Window size loading from config
 */
ConfigManager.readWindowSize = function(config, name) {
    var value = config[name];
    if (value !== undefined) {
        return Number(value).clamp(windowSizeMin(), windowSizeMax());
    } else {
        return 100;
    }
};

/**
 * ●Get display state
 */
var _Window_Options_statusText = Window_Options.prototype.statusText;
Window_Options.prototype.statusText = function(index) {
    var symbol = this.commandSymbol(index);
    var value = this.getConfigValue(symbol);

    if (isWindowsSizeSymbol(symbol)) {
        return windowSizeStatusText(value);
    }

    return _Window_Options_statusText.apply(this, arguments);
};

/**
 * ●Window size display name
 */
function windowSizeStatusText(value) {
    // Size display
    if (pOptionDispType == "size") {
        return getWindowWidth() + "*" + getWindowHeight();
    }
    // ％表示
    return Math.round(value * 10) / 10 + '%';
}

/**
 * ●Round to avoid too fine values
 */
function windowSizeRound(value) {
    // Set minimum and maximum values, and set 100 or less than 1 to their respective values.
    // (A painstaking fine-tuning……)
    if (Math.abs(value - windowSizeMin()) < 1) {
        value = windowSizeMin();
    } else if (Math.abs(value - windowSizeMax()) < 1) {
        value = windowSizeMax();
    } else if (Math.abs(value - 100) < 1) {
        value = 100;
    }

    // Up to the second decimal place
    return Math.round(value * 100) / 100;
}

/**
 * ●Decision Key
 */
var _Window_Options_processOk = Window_Options.prototype.processOk;
Window_Options.prototype.processOk = function() {
    var index = this.index();
    var symbol = this.commandSymbol(index);
    var value = this.getConfigValue(symbol);

    if (isWindowsSizeSymbol(symbol)) {
        value += windowSizeOffset();
        value = windowSizeRound(value);

        if (value > windowSizeMax()) {
            value = windowSizeMin();
        }
        this.changeWindowSizeValue(symbol, value);
        return;
    }
    
    _Window_Options_processOk.apply(this, arguments);
};

/**
 * ●Cursor Right
 */
var _Window_Options_cursorRight = Window_Options.prototype.cursorRight;
Window_Options.prototype.cursorRight = function(wrap) {
    var index = this.index();
    var symbol = this.commandSymbol(index);
    var value = this.getConfigValue(symbol);

    if (isWindowsSizeSymbol(symbol)) {
        value += windowSizeOffset();
        value = windowSizeRound(value);
        this.changeWindowSizeValue(symbol, value);
        return;
    }

    _Window_Options_cursorRight.apply(this, arguments);
};

/**
 * ●Cursor Left
 */
var _Window_Options_cursorLeft = Window_Options.prototype.cursorLeft;
Window_Options.prototype.cursorLeft = function(wrap) {
    var index = this.index();
    var symbol = this.commandSymbol(index);
    var value = this.getConfigValue(symbol);

    if (isWindowsSizeSymbol(symbol)) {
        value -= windowSizeOffset();
        value = windowSizeRound(value);
        this.changeWindowSizeValue(symbol, value);
        return;
    }

    _Window_Options_cursorLeft.apply(this, arguments);
};

/**
 * 【Custom】Change window size value
 */
Window_Options.prototype.changeWindowSizeValue = function(symbol, value) {
    value = value.clamp(windowSizeMin(), windowSizeMax());
    this.changeValue(symbol, value);

    // In the case of MZ
    if (Utils.RPGMAKER_NAME != "MV") {
        // Prohibit selection by touch
        // To avoid changing the selection state due to window size changes
        this._noTouchSelect = true;
    }
};

// In the case of MZ
if (Utils.RPGMAKER_NAME != "MV") {
    /**
     * ●Touch selection processing
     */
    const _Window_Options_onTouchSelect = Window_Options.prototype.onTouchSelect;
    Window_Options.prototype.onTouchSelect = function(trigger) {
        // Prohibit touch selection!
        if (this._noTouchSelect) {
            this._noTouchSelect = undefined;
            return;
        }

        _Window_Options_onTouchSelect.apply(this, arguments);
    };
}

/**
 * ●Add window size item
 */
const _Window_Options_makeCommandList = Window_Options.prototype.makeCommandList;
Window_Options.prototype.makeCommandList = function() {
    _Window_Options_makeCommandList.apply(this, arguments);

    this._list.splice(pOptionPosition, 0, { name: pOptionName, symbol: WINDOW_SIZE_SYMBOL, enabled: true, ext: null});

    // Conflict handling with Mano_InputConfig.js
    if (this._gamepadOptionIndex >= pOptionPosition) {
        this._gamepadOptionIndex++;
    }
    if (this._keyboardConfigIndex >= pOptionPosition) {
        this._keyboardConfigIndex++;
    }
};

/**
 * ●Settings applied
 */
var _Window_Options_setConfigValue = Window_Options.prototype.setConfigValue;
Window_Options.prototype.setConfigValue = function(symbol, volume) {
    _Window_Options_setConfigValue.apply(this, arguments);

    if (isWindowsSizeSymbol(symbol)) {
        // Window size updated
        changeWindowSize();
    }
};

/**
 * ●Is there an option for window size?
 */
function isWindowsSizeSymbol(symbol) {
    if (symbol == WINDOW_SIZE_SYMBOL) {
        return true;
    }
    return false;
}

/**
 * ●Add command count
 */
const _Scene_Options_maxCommands = Scene_Options.prototype.maxCommands;
Scene_Options.prototype.maxCommands = function() {
    return _Scene_Options_maxCommands.apply(this, arguments) + 1;
};

})();
