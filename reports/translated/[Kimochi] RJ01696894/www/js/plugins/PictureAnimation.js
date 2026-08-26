//=============================================================================
// PictureAnimation.js
// ----------------------------------------------------------------------------
// (C) 2015 Triacontane
// This software is released under the MIT License.
// http://opensource.org/licenses/mit-license.php
// ----------------------------------------------------------------------------
// Version
// 1.6.1 2020/12/06 Added handling to mark as complete when reaching the last frame of the last cell in the function addition from 1.6.0
// 1.6.0 2020/10/24 Added setting to not proceed to the next command until the picture animation completes
// 1.5.10 2020/01/30 Added script help to retrieve the current cell number
// 1.5.9 2020/01/26 Fixed an issue where a semi-transparent picture remained after replacing a picture during an animation
// 1.5.8 2019/10/27 Fixed an issue where the end position of non-loop animations was incorrect when the animation type was not 1
// 1.5.7 2019/04/20 Modified so that the sound in command 'PA_SOUND' for the first cell plays immediately when the animation starts
// 1.5.6 2019/03/03 Fixed the issue where animations and sound effects of pictures outside the scene are disabled
// 1.5.5 2019/02/13 Fixed the issue where specifying index 0 (the first cell) with the command 'PA_SET_CELL' does not function
// 1.5.4 2019/02/09 Fixed the issue where an error occurs when animating without specifying a cell pattern in 1.5.3
// 1.5.3 2019/02/27 Fixed the issue where the first cell is always the first one when directly specifying a cell pattern for animation playback
// 1.5.2 2018/03/04 Fixed the issue where displaying an animation picture vertically or horizontally and then displaying the same picture with the same number may not display correctly
// 1.5.1 2017/08/22 Fixed the issue where an error occurs when switching to another animation with fewer cells during animation playback
// 1.5.0 2017/07/03 Added the functionality to choose whether to return to the first cell after the end of a non-looping animation
// 1.4.0 2016/09/03 Added the functionality to play a specified SE in sync with the animation
// 1.3.2 2016/05/11 Fixed the issue where an error occurs the second time displaying an animation with cross-fade specified
// 1.3.1 2016/03/15 Resolved the conflict with the plugin 'PictureOnAnimation' for displaying battle animations on pictures
//                  Fix an issue where cross-fading a picture centered on the origin causes the display position to shift
// 1.3.0 2016/02/28 Add a feature to link cell number with variables, slightly reducing processing load
//                  Fix an issue where an error occurs when trying to display a picture of the sky
// 1.2.3 2016/02/07 Fix an issue where picture animations could not be performed on the battle screen
// 1.2.2 2016/01/24 Fix an issue where an error occurs when trying to display a picture of the sky
// 1.2.1 2016/01/16 Fix an issue where an error occurs when specifying the same image and performing picture display → animation preparation → picture display in sequence
//                  Fix an issue where an error occurs when specifying the same image and performing picture display → animation preparation → picture display in sequence
// 1.2.0 2016/01/04 Add a feature to freely specify cell patterns
//                  Expand the maximum number of cells from 100 to 200
// 1.1.2 2015/12/24 Added support for image switching using cross-fade
// 1.1.1 2015/12/21 You can now specify picture filenames in sequential numbering format
//                  A feature to forcibly end animations has been added
// 1.0.0 2015/12/19 Initial release
// ----------------------------------------------------------------------------
// [Blog]   : https://triacontane.blogspot.jp/
// [Twitter]: https://twitter.com/triacontane/
// [GitHub] : https://github.com/triacontane/
//=============================================================================

/*:
 * @plugindesc [アニメーション]　ピクチャのアニメーションプラグイン
 * @author トリアコンタン
 *
 * @param 最初のセルに戻る
 * @desc ループしないアニメーションの終了後、最初のセルに戻ります。無効にすると最後のセルで止まります。
 * @default true
 * @type boolean
 *
 * @help 指定したフレーム間隔でピクチャをアニメーションします。
 * Prepare the cell images you want to animate (※)
 * Please input the following command.
 *
 * 1. Prepare animation for picture (Plugin command)
 * 2. Display picture (Regular event command)
 * 3. Start picture animation (Plugin command)
 * 4. End picture animation (Plugin command)
 *
 * ※There are three methods for placement.
 *  Vertical: Arrange cells vertically and combine them into one file.
 *  Horizontal: Arrange cells horizontally and combine them into one file.
 *  Sequential: Prepare multiple images with sequential cell numbers. (original part can be any string)
 *   original00.png (original file specified for picture display)
 *   original01.png
 *   original02.png...
 *
 * Note! When using the sequential method for placement, there is a possibility that
 * unused files may be excluded during deployment.
 * In that case, you may need to reinsert the deleted files, etc.
 *
 * Additionally, you can directly specify cell numbers from plugin commands or
 * link cell numbers with variable values.
 * This can be used for performances like paper theater, or changing the display state of character images based on conditions.
 * It is valid.
 *
 * Plugin command details
 *  Execute via the event command "Plugin Command".
 *  (Separate parameters with a space)
 *
 *  PA_INIT or
 *  ピクチャのアニメーション準備 [セル数] [フレーム数] [セル配置方法] [フェード時間]
 *  Prepare to make the picture an animation target.
 *  Please execute just before "Picture Display".
 *  Number of Cells: The number of cell drawings to animate (maximum 200 images)
 *  Frame Count: The number of frames between animations (set at least to 1)
 *  Cell Placement Direction: The method of arranging cells (vertical or horizontal or sequential)
 *  Fade Time: Number of frames for image switching (set to 0 to not use fade)
 *  Example: PA_INIT 4 10 sequential 20
 *
 *  PA_START or
 *  ピクチャのアニメーション開始 [ピクチャ番号] [アニメーションタイプ] [カスタムパターン配列]
 *  　The animation will start for the specified picture number.
 *  　The animation will automatically stop after one cycle.
 *
 *  　There are three types of animation patterns.
 *  　　Example: If the cell count is 4,
 *  　　　Type 1: 1→2→3→4→1→2→3→4...
 *  　　　Type 2: 1→2→3→4→3→2→1→2...
 *  　　　Type 3: Specify the order in an array (the minimum cell value is 1)
 *  Example usage: PA_START 1 2
 *  　　　　PA_START 1 3 [1,2,1,3,1,4]
 *
 *  PA_START_LOOP or
 *  ピクチャのループアニメーション開始 [ピクチャ番号] [アニメーションタイプ] [カスタムパターン配列]
 *  　The animation will start for the specified picture number.
 *  　The animation will continue until explicitly stopped.
 *  Example: PA_START_LOOP 1 2
 *  　　　　PA_START_LOOP 1 3 [1,2,1,3,1,4]
 *
 *  PA_STOP or
 *  ピクチャのアニメーション終了 [ピクチャ番号]
 *  　Stops the animation of the specified picture number.
 *  　The animation stops when it returns to the topmost cell.
 *  Example: PA_STOP 1
 *
 *  PA_STOP_FORCE or
 *  ピクチャのアニメーション強制終了 [ピクチャ番号]
 *  　Stops the animation of the specified picture number.
 *  　The animation stops on the currently displayed cell.
 *  Example: PA_STOP_FORCE 1
 *
 *  PA_SET_CELL or
 *  ピクチャのアニメーションセル設定 [ピクチャ番号] [セル番号] [ウェイトあり]
 *  　Directly sets the animation cell. (The minimum cell value is 1.)
 *  　This is effective when you want to animate at any timing.
 *  　Setting Wait will make the event execution wait during the crossfade.
 *  Example: PA_SET_CELL 1 3 ウェイトあり
 *
 *  PA_PROG_CELL or
 *  ピクチャのアニメーションセル進行 [ピクチャ番号] [ウェイトあり]
 *  　It advances the animation cell by one.
 *  　This is effective when you want to animate at any timing.
 *  　Setting Wait will make the event execution wait during the crossfade.
 *  Example: PA_PROG_CELL 1 ウェイトあり
 *
 *  PA_SET_VARIABLE or
 *  ピクチャのアニメーションセル変数の設定 [ピクチャ番号] [変数番号]
 *  　It links the animation cell to a specified variable.
 *  　The displayed cell will change automatically when the variable's value changes.
 *  Example: PA_SET_VARIABLE 1 2
 *
 *  PA_SOUND or
 *  ピクチャのアニメーション効果音予約 [セル番号]
 *   The sound effect will be played when the animation cell changes.
 *   If you execute the event command 'Play SE' immediately after this command,
 *   the SE will not be played at that location, but will be played at the specified timing after the picture animation starts.
 *
 *  　Always execute before the animation of the picture starts.
 *
 *  PA_WAIT or
 *  ピクチャのアニメーションウェイト [ピクチャ番号]
 * 　　It will wait until the animation of the specified picture number finishes.
 *
 * Script Details
 *
 * Gets the current cell number for the picture during the animation.
 * The event command "Variable Manipulation" or "Condition Branch" can use this.
 * It will cause an error if executed when the picture is not being displayed.
 * $gameScreen.picture(1).cell; // Get the cell of picture number [1]
 *
 * Terms of Use:
 *  Modification and redistribution without the author's consent are allowed,
 *  and there are no restrictions on usage (commercial, 18+ use, etc.).
 *  This plugin is now yours.
 */
(function() {
    'use strict';
    var pluginName = 'PictureAnimation';

    var settings = {
        /* maxCellAnimation: Maximum value of cell count */
        maxCellAnimation: 200
    };

    var getParamString = function(paramNames) {
        if (!Array.isArray(paramNames)) paramNames = [paramNames];
        for (var i = 0; i < paramNames.length; i++) {
            var name = PluginManager.parameters(pluginName)[paramNames[i]];
            if (name) return name;
        }
        return '';
    };

    var getParamBoolean = function(paramNames) {
        var value = getParamString(paramNames);
        return value.toUpperCase() === 'ON' || value.toUpperCase() === 'TRUE';
    };

    //=============================================================================
    // Local function
    // Formats and checks the plugin parameters or plugin command parameters
    //=============================================================================
    var getCommandName = function(command) {
        return (command || '').toUpperCase();
    };

    var getArgArrayString = function(args, upperFlg) {
        var values = getArgString(args, upperFlg);
        return (values || '').split(',');
    };

    var getArgArrayNumber = function(args, min, max) {
        if (!args) {
            return [];
        }
        var values = getArgArrayString(args.substring(1, args.length - 1), false);
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        for (var i = 0; i < values.length; i++) values[i] = (parseInt(values[i], 10) || 0).clamp(min, max);
        return values;
    };

    var getArgString = function(arg, upperFlg) {
        arg = convertEscapeCharacters(arg);
        return upperFlg ? arg.toUpperCase() : arg;
    };

    var getArgNumber = function(arg, min, max) {
        if (arguments.length < 2) min = -Infinity;
        if (arguments.length < 3) max = Infinity;
        return (parseInt(convertEscapeCharacters(arg), 10) || 0).clamp(min, max);
    };

    var convertEscapeCharacters = function(text) {
        if (text == null) text = '';
        var window = SceneManager._scene._windowLayer.children[0];
        return window ? window.convertEscapeCharacters(text) : text;
    };

    //=============================================================================
    // Parameter Retrieval and Formatting
    //=============================================================================
    var param               = {};
    param.returnToFirstCell = getParamBoolean(['ReturnToFirstCell', 'Return to first cell']);

    //=============================================================================
    // Game_Interpreter
    //  Define additional plugin commands.
    //=============================================================================
    var _Game_Interpreter_pluginCommand      = Game_Interpreter.prototype.pluginCommand;
    Game_Interpreter.prototype.pluginCommand = function(command, args) {
        _Game_Interpreter_pluginCommand.call(this, command, args);
        this.pluginCommandPictureAnimation(command, args);
    };

    Game_Interpreter.prototype.pluginCommandPictureAnimation = function(command, args) {
        var pictureNum, animationType, picture, cellNumber, frameNumber, direction, fadeDuration, wait, customArray;
        switch (getCommandName(command)) {
            case 'PA_INIT' :
            case 'Prepare animation for the picture':
                cellNumber   = getArgNumber(args[0], 1, settings.maxCellAnimation);
                frameNumber  = getArgNumber(args[1], 1, 9999);
                direction    = getArgString(args[2], true) || '縦';
                fadeDuration = getArgNumber(args[3], 0, 9999) || 0;
                $gameScreen.setPicturesAnimation(cellNumber, frameNumber, direction, fadeDuration);
                break;
            case 'PA_SOUND' :
            case 'Reserve sound effect for the picture's animation':
                cellNumber = getArgNumber(args[0], 1, settings.maxCellAnimation);
                this.reservePaSound(cellNumber);
                break;
            case 'PA_START' :
            case 'Start the picture's animation':
                pictureNum    = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                animationType = getArgNumber(args[1], 1, 3);
                customArray   = getArgArrayNumber(args[2], 1, settings.maxCellAnimation);
                picture       = $gameScreen.picture(pictureNum);
                if (picture) picture.startAnimationFrame(animationType, false, customArray);
                break;
            case 'PA_START_LOOP' :
            case 'Start the picture's loop animation':
                pictureNum    = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                animationType = getArgNumber(args[1], 1, 3);
                customArray   = getArgArrayNumber(args[2], 1, settings.maxCellAnimation);
                picture       = $gameScreen.picture(pictureNum);
                if (picture) picture.startAnimationFrame(animationType, true, customArray);
                break;
            case 'PA_STOP' :
            case 'Picture animation end':
                pictureNum = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                picture    = $gameScreen.picture(pictureNum);
                if (picture) picture.stopAnimationFrame(false);
                break;
            case 'PA_STOP_FORCE' :
            case 'Forced end of picture animation':
                pictureNum = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                picture    = $gameScreen.picture(pictureNum);
                if (picture) picture.stopAnimationFrame(true);
                break;
            case 'PA_SET_CELL' :
            case 'Set picture animation cells':
                pictureNum = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                cellNumber = getArgNumber(args[1], 0, settings.maxCellAnimation);
                wait       = getArgString(args[2]);
                picture    = $gameScreen.picture(pictureNum);
                if (picture) {
                    if (wait === 'With weight' || wait.toUpperCase() === 'WAIT') this.wait(picture._fadeDuration);
                    picture.cell = cellNumber;
                }
                break;
            case 'PA_PROG_CELL' :
            case 'Progress of picture animation cells':
                pictureNum = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                wait       = getArgString(args[1]);
                picture    = $gameScreen.picture(pictureNum);
                if (picture) {
                    if (wait === 'With weight' || wait.toUpperCase() === 'WAIT') this.wait(picture._fadeDuration);
                    picture.addCellCount();
                }
                break;
            case 'PA_SET_VARIABLE' :
            case 'Set picture animation cell variables':
                pictureNum = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                picture    = $gameScreen.picture(pictureNum);
                if (picture) picture.linkToVariable(getArgNumber(args[1]));
                break;
            case 'PA_WAIT':
            case 'Picture animation weight':
                pictureNum = getArgNumber(args[0], 1, $gameScreen.maxPictures());
                picture    = $gameScreen.picture(pictureNum);
                if (picture) {
                    this.waitForPictureAnimation(pictureNum);
                }
                break;
        }
    };

    Game_Interpreter.prototype.reservePaSound = function(cellNumber) {
        this._paSoundFrame = cellNumber;
    };

    var _Game_Interpreter_command250      = Game_Interpreter.prototype.command250;
    Game_Interpreter.prototype.command250 = function() {
        if (this._paSoundFrame) {
            var se = this._params[0];
            AudioManager.loadStaticSe(se);
            $gameScreen.addPaSound(se, this._paSoundFrame);
            this._paSoundFrame = null;
            return true;
        }
        return _Game_Interpreter_command250.apply(this, arguments);
    };

    const _Game_Interpreter_updateWaitMode = Game_Interpreter.prototype.updateWaitMode;
    Game_Interpreter.prototype.updateWaitMode = function() {
        if (this._waitMode === 'pictureAnimation') {
            const picture = $gameScreen.picture(this._waitPictureId);
            if (picture && picture.isAnimationPlaying()) {
                return true;
            } else {
                this._waitPictureId = 0;
                this._waitMode = '';
                return false;
            }
        } else {
            return _Game_Interpreter_updateWaitMode.apply(this, arguments);
        }
    };

    Game_Interpreter.prototype.waitForPictureAnimation = function(pictureId) {
        this.setWaitMode('pictureAnimation');
        this._waitPictureId = pictureId;
    };

    //=============================================================================
    // Game_Screen
    // This plugin additionally stores related animation information.
    //=============================================================================
    Game_Screen.prototype.setPicturesAnimation = function(cellNumber, frameNumber, direction, fadeDuration) {
        this._paCellNumber   = cellNumber;
        this._paFrameNumber  = frameNumber;
        this._paDirection    = direction;
        this._paFadeDuration = fadeDuration;
    };

    Game_Screen.prototype.addPaSound = function(sound, frame) {
        if (!this._paSounds) this._paSounds = [];
        this._paSounds[frame] = sound;
    };

    Game_Screen.prototype.clearPicturesAnimation = function() {
        this._paCellNumber   = 1;
        this._paFrameNumber  = 1;
        this._paDirection    = '';
        this._paFadeDuration = 0;
        this._paSounds       = null;
    };

    var _Game_Screen_showPicture      = Game_Screen.prototype.showPicture;
    Game_Screen.prototype.showPicture = function(pictureId, name, origin, x, y,
                                                 scaleX, scaleY, opacity, blendMode) {
        _Game_Screen_showPicture.apply(this, arguments);
        var realPictureId = this.realPictureId(pictureId);
        if (this._paCellNumber > 1) {
            this._pictures[realPictureId].setAnimationFrameInit(
                this._paCellNumber, this._paFrameNumber, this._paDirection, this._paFadeDuration, this._paSounds);
            this.clearPicturesAnimation();
        }
    };

    Game_Screen.prototype.isActivePicture = function(picture) {
        var realId = this._pictures.indexOf(picture);
        return realId > this.maxPictures() === $gameParty.inBattle();
    };

    //=============================================================================
    // Game_Picture
    // This plugin additionally stores related animation information.
    //=============================================================================
    var _Game_Picture_initialize      = Game_Picture.prototype.initialize;
    Game_Picture.prototype.initialize = function() {
        _Game_Picture_initialize.call(this);
        this.initAnimationFrameInfo();
    };

    Game_Picture.prototype.initAnimationFrameInfo = function() {
        this._cellNumber        = 1;
        this._frameNumber       = 1;
        this._cellCount         = 0;
        this._frameCount        = 0;
        this._animationType     = 0;
        this._customArray       = null;
        this._loopFlg           = false;
        this._direction         = '';
        this._fadeDuration      = 0;
        this._fadeDurationCount = 0;
        this._prevCellCount     = 0;
        this._animationFlg      = false;
        this._linkedVariable    = 0;
        this._cellSes           = [];
    };

    Game_Picture.prototype.direction = function() {
        return this._direction;
    };

    Game_Picture.prototype.cellNumber = function() {
        return this._cellNumber;
    };

    Game_Picture.prototype.prevCellCount = function() {
        return this._prevCellCount;
    };

    Game_Picture.prototype.isMulti = function() {
        var dir = this.direction();
        return dir === 'Sequential numbers' || dir === 'N';
    };

    /**
     * The cellCount of the Game_Picture (0 to cellNumber).
     *
     * @property cellCount
     * @type Number
     */
    Object.defineProperty(Game_Picture.prototype, 'cell', {
        get: function() {
            if (this._linkedVariable > 0) {
                return $gameVariables.value(this._linkedVariable) % this._cellNumber;
            }
            switch (this._animationType) {
                case 3:
                    return (this._customArray[this._cellCount] - 1).clamp(0, this._cellNumber - 1);
                case 2:
                    return this._cellNumber - 1 - Math.abs(this._cellCount - (this._cellNumber - 1));
                case 1:
                    return this._cellCount;
                default:
                    return this._cellCount;
            }
        },
        set: function(value) {
            var newCellCount = value % this.getCellNumber();
            if (this._cellCount !== newCellCount) {
                this._prevCellCount     = this.cell;
                this._fadeDurationCount = this._fadeDuration;
            }
            this._cellCount = newCellCount;
        }
    });

    Game_Picture.prototype.getCellNumber = function() {
        switch (this._animationType) {
            case 3:
                return this._customArray.length;
            case 2:
                return (this._cellNumber - 1) * 2;
            case 1:
                return this._cellNumber;
            default:
                return this._cellNumber;
        }
    };

    var _Game_Picture_update      = Game_Picture.prototype.update;
    Game_Picture.prototype.update = function() {
        _Game_Picture_update.call(this);
        if (this.isFading()) {
            this.updateFading();
        } else if (this.hasAnimationFrame() && this.isActive()) {
            this.updateAnimationFrame();
        } else if (this._lastFrameCount > 0) {
            this._lastFrameCount--;
        }
    };

    Game_Picture.prototype.linkToVariable = function(variableNumber) {
        this._linkedVariable = variableNumber.clamp(1, $dataSystem.variables.length);
    };

    Game_Picture.prototype.updateAnimationFrame = function() {
        this._frameCount = (this._frameCount + 1) % this._frameNumber;
        if (this._frameCount === 0) {
            this.addCellCount();
            this.playCellSe();
            if (this.isEndFirstLoop() && !this._loopFlg) {
                this._animationFlg = false;
                this._lastFrameCount = this._frameNumber;
            }
        }
    };

    Game_Picture.prototype.isEndFirstLoop = function() {
        return this._cellCount === (param.returnToFirstCell ? 0 : this.getCellNumber() - 1);
    };

    Game_Picture.prototype.updateFading = function() {
        this._fadeDurationCount--;
    };

    Game_Picture.prototype.prevCellOpacity = function() {
        if (this._fadeDuration === 0) return 0;
        return this.opacity() / this._fadeDuration * this._fadeDurationCount;
    };

    Game_Picture.prototype.addCellCount = function() {
        this.cell = this._cellCount + 1;
    };

    Game_Picture.prototype.playCellSe = function() {
        var se = this._cellSes[this.cell + 1];
        if (se) {
            AudioManager.playSe(se);
        }
    };

    Game_Picture.prototype.setAnimationFrameInit = function(cellNumber, frameNumber, direction, fadeDuration, cellSes) {
        this._cellNumber   = cellNumber;
        this._frameNumber  = frameNumber;
        this._frameCount   = 0;
        this._cellCount    = 0;
        this._direction    = direction;
        this._fadeDuration = fadeDuration;
        this._cellSes      = cellSes || [];
    };

    Game_Picture.prototype.startAnimationFrame = function(animationType, loopFlg, customArray) {
        this._animationType = animationType;
        this._customArray   = customArray;
        this._animationFlg  = true;
        this._loopFlg       = loopFlg;
        if (this._cellNumber <= this._cellCount) {
            this._cellCount = this._cellNumber - 1;
        }
        this.playCellSe();
    };

    Game_Picture.prototype.stopAnimationFrame = function(forceFlg) {
        this._loopFlg = false;
        if (forceFlg) {
            this._animationFlg = false;
        }
    };

    Game_Picture.prototype.hasAnimationFrame = function() {
        return this._animationFlg;
    };

    Game_Picture.prototype.isFading = function() {
        return this._fadeDurationCount !== 0;
    };

    Game_Picture.prototype.isAnimationPlaying = function() {
        return this.hasAnimationFrame() || this.isFading() || this._lastFrameCount > 0;
    };

    Game_Picture.prototype.isNeedFade = function() {
        return this._fadeDuration !== 0;
    };

    Game_Picture.prototype.isActive = function() {
        return $gameScreen.isActivePicture(this);
    };

    //=============================================================================
    // Sprite_Picture
    // This plugin additionally stores related animation information.
    //=============================================================================
    var _Sprite_Picture_initialize      = Sprite_Picture.prototype.initialize;
    Sprite_Picture.prototype.initialize = function(pictureId) {
        this._prevSprite = null;
        _Sprite_Picture_initialize.apply(this, arguments);
    };

    var _Sprite_Picture_update      = Sprite_Picture.prototype.update;
    Sprite_Picture.prototype.update = function() {
        _Sprite_Picture_update.apply(this, arguments);
        var picture = this.picture();
        if (picture && picture.name()) {
            if (picture.isMulti() && !this._bitmaps) {
                this.loadAnimationBitmap();
            }
            if (this.isBitmapReady()) {
                this.updateAnimationFrame(this, picture.cell);
                if (picture.isNeedFade()) this.updateFading();
            }
        }
    };

    var _Sprite_Picture_updateBitmap      = Sprite_Picture.prototype.updateBitmap;
    Sprite_Picture.prototype.updateBitmap = function() {
        _Sprite_Picture_updateBitmap.apply(this, arguments);
        if (!this.picture()) {
            this._bitmaps = null;
            if (this._prevSprite) {
                this._prevSprite.bitmap = null;
            }
        }
    };

    Sprite_Picture.prototype.updateFading = function() {
        if (!this._prevSprite) {
            this.makePrevSprite();
        }
        if (!this._prevSprite.bitmap) {
            this.makePrevBitmap();
        }
        var picture = this.picture();
        if (picture.isFading()) {
            this._prevSprite.visible = true;
            this.updateAnimationFrame(this._prevSprite, picture.prevCellCount());
            this._prevSprite.opacity = picture.prevCellOpacity();
        } else {
            this._prevSprite.visible = false;
        }
    };

    Sprite_Picture.prototype.updateAnimationFrame = function(sprite, cellCount) {
        switch (this.picture().direction()) {
            case 'Sequential numbers':
            case 'N':
                sprite.bitmap = this._bitmaps[cellCount];
                sprite.setFrame(0, 0, sprite.bitmap.width, sprite.bitmap.height);
                break;
            case '縦':
            case 'V':
                var height = sprite.bitmap.height / this.picture().cellNumber();
                var y      = cellCount * height;
                sprite.setFrame(0, y, sprite.bitmap.width, height);
                break;
            case '横':
            case 'H':
                var width = sprite.bitmap.width / this.picture().cellNumber();
                var x     = cellCount * width;
                sprite.setFrame(x, 0, width, sprite.bitmap.height);
                break;
            default:
                sprite.setFrame(0, 0, this.bitmap.width, this.bitmap.height);
        }
    };

    var _Sprite_Picture_loadBitmap      = Sprite_Picture.prototype.loadBitmap;
    Sprite_Picture.prototype.loadBitmap = function() {
        _Sprite_Picture_loadBitmap.apply(this, arguments);
        this._bitmapReady = false;
        this._bitmaps     = null;
        if (this._prevSprite) {
            this._prevSprite.visible = false;
        }
    };

    Sprite_Picture.prototype.loadAnimationBitmap = function() {
        var cellNumber = this.picture().cellNumber();
        var cellDigit  = cellNumber.toString().length;
        this._bitmaps  = [this.bitmap];
        for (var i = 1; i < cellNumber; i++) {
            var filename     = this._pictureName.substr(0, this._pictureName.length - cellDigit) + i.padZero(cellDigit);
            this._bitmaps[i] = ImageManager.loadPicture(filename);
        }
        this._bitmapReady = false;
    };

    Sprite_Picture.prototype.makePrevSprite = function() {
        this._prevSprite         = new Sprite();
        this._prevSprite.visible = false;
        this.addChild(this._prevSprite);
    };

    Sprite_Picture.prototype.makePrevBitmap = function() {
        this._prevSprite.bitmap   = this.bitmap;
        this._prevSprite.anchor.x = this.anchor.x;
        this._prevSprite.anchor.y = this.anchor.y;
    };

    Sprite_Picture.prototype.isBitmapReady = function() {
        if (!this.bitmap) return false;
        if (this._bitmapReady) return true;
        var result;
        if (this.picture().isMulti()) {
            result = this._bitmaps.every(function(bitmap) {
                return bitmap.isReady();
            });
        } else {
            result = this.bitmap.isReady();
        }
        this._bitmapReady = result;
        return result;
    };
})();
