//=============================================================================
// DisplayNumber.js
//=============================================================================
/*:
 * @plugindesc 数字をアニメーションして表示する
 * @author hami
 *
 * @help
 * Start startNumberA(from, to, totalFrame);  Example: startNumberA(0, 50, 60);
 * Stop stopNumber();
 *
 * Start startNumberB();  A bar that stretches from x582, y319 to x860 from left to right over 120 frames.
 * Stop stopNumberB();
 */

(function() {

    class NumberDisplay {
        constructor(scene) {
            this._layer = scene._myLayer;

            this._numSize   = 120;
            this._barWidth  = 134;
            this._barHeight = 21;

            // ===== A =====
            this._barBitmap = new Bitmap(this._barWidth, this._barHeight);
            this._barBitmap._context.imageSmoothingEnabled = false;
            this._barSprite = new Sprite(this._barBitmap);
            this._barSprite.x = 713;
            this._barSprite.y = 420;
            this._barSprite.visible = false;
            this._layer.addChild(this._barSprite);

            this._numBitmapA = new Bitmap(this._numSize, this._numSize);
            this._numBitmapA._context.imageSmoothingEnabled = false;
            this._numSpriteA = new Sprite(this._numBitmapA);
            this._numSpriteA.x = 727;
            this._numSpriteA.y = 371;
            this._numSpriteA.visible = false;
            this._layer.addChild(this._numSpriteA);

            // Gauge memory point
            this._rectBitmap = new Bitmap(2, 4);
            const rectCtx = this._rectBitmap._context;
            rectCtx.fillStyle = '#8a8d99';
            rectCtx.fillRect(0, 0, 2, 4);
            this._rectBitmap._setDirty();
            this._rectSprite = new Sprite(this._rectBitmap);
            this._rectSprite.x = 779;
            this._rectSprite.y = 437;
            this._rectSprite.visible = false;
            this._layer.addChild(this._rectSprite);

            this._numberBitmap = ImageManager.loadPicture('UI_number_2');

            // Frame management
            this._frameA = 0;
            this._playingA = false;
            this._fromA = 0;
            this._toA = 0;
            this._totalFrameA = 60;

            // ===== B =====
            this._startXB     = 582;
            this._endXB       = 861;
            this._yB          = 319;
            this._heightB     = 20;
            this._widthB      = this._endXB - this._startXB;
            this._totalFrameB = 120;

            this._barBitmapB = new Bitmap(this._widthB, this._heightB);
            this._barBitmapB._context.imageSmoothingEnabled = false;
            this._barSpriteB = new Sprite(this._barBitmapB);
            this._barSpriteB.x = this._startXB;
            this._barSpriteB.y = this._yB;
            this._barSpriteB.visible = false;
            this._layer.addChild(this._barSpriteB);

            this._frameB = 0;
            this._playingB = false;
        }

        startA(from, to, totalFrame) {
            this._fromA = from;
            this._toA = to;
            this._totalFrameA = totalFrame || 60;
            this._frameA = 0;
            this._playingA = true;
            this._numSpriteA.visible = true;
            this._barSprite.visible = true;
            this._rectSprite.visible = true;
        }

        stop() {
            this._playingA = false;
            this._numSpriteA.visible = false;
            this._barSprite.visible = false;
            this._rectSprite.visible = false;
        }

        startB() {
            this._frameB = 0;
            this._playingB = true;
            this._barSpriteB.visible = true;
        }

        stopB() {
            this._playingB = false;
            this._barSpriteB.visible = false;
            const ctx = this._barBitmapB._context;
            ctx.clearRect(0, 0, this._widthB, this._heightB);
            this._barBitmapB._setDirty();
        }

        update() {
            if (this._playingA) {
                if (this._frameA >= this._totalFrameA) {
                    this._playingA = false;
                } else {
                    this._frameA++;
                    const currentA = this._updateNumber(
                        this._numBitmapA, this._numberBitmap,
                        this._frameA, this._totalFrameA,
                        this._fromA, this._toA, true
                    );

                    this._updateBar(currentA);
                }
            }

            if (this._playingB) {
                if (this._frameB >= this._totalFrameB) {
                    this._playingB = false;
                } else {
                    this._frameB++;
                    this._updateBarB(this._frameB, this._totalFrameB);
                }
            }
        }

        // Common number drawing process
        _updateNumber(bitmap, numberBitmap, frame, totalFrame, from, to, withPercent) {
            const charWidth  = 12;
            const charHeight = 18;
            const numSize    = this._numSize;
            const rightEdge  = numSize;

            const rate    = frame / totalFrame;
            const current = Math.round(from + (to - from) * rate);

            const ctx = bitmap._context;
            ctx.imageSmoothingEnabled = false;
            ctx.clearRect(0, 0, numSize, numSize);

            const str = withPercent ? String(current) + '%' : String(current);

            for (let i = 0; i < str.length; i++) {
                const ch    = str[i];
                const srcX  = ch === '%' ? 10 * charWidth : parseInt(ch) * charWidth;
                const drawX = rightEdge - (str.length - i) * charWidth;
                bitmap.blt(numberBitmap, srcX, 0, charWidth, charHeight, drawX, numSize / 2 - charHeight / 2);
            }
            bitmap._setDirty();
            return current;
        }

        _updateBar(currentA) {
            const barWidth  = this._barWidth;
            const barHeight = this._barHeight;
            const dotSize   = 3;

            const barCtx = this._barBitmap._context;
            barCtx.imageSmoothingEnabled = false;
            barCtx.clearRect(0, 0, barWidth, barHeight);
            const currentWidth = Math.round(barWidth * currentA / 100);
            for (let by = 0; by < barHeight; by += dotSize) {
                for (let bx = barWidth - currentWidth; bx < barWidth; bx += dotSize) {
                    barCtx.fillStyle = '#bdc1cd';
                    barCtx.fillRect(bx, by, dotSize, dotSize);
                }
            }
            this._barBitmap._setDirty();
        }

        // Drawing process for the bar that stretches from x582, y319 to x860 from left to right.
        _updateBarB(frame, totalFrame) {
            const width  = this._widthB;
            const height = this._heightB;

            const rate = frame / totalFrame;
            const currentWidth = Math.round(width * rate);

            const ctx = this._barBitmapB._context;
            ctx.imageSmoothingEnabled = false;
            ctx.clearRect(0, 0, width, height);
            ctx.fillStyle = '#bdc1cd';
            ctx.fillRect(0, 0, currentWidth, height);
            this._barBitmapB._setDirty();
        }
    }

    ////////////////////////////
    //  Scene_Map.createAllWindows
    ////////////////////////////
    const _Scene_Map_createAllWindows = Scene_Map.prototype.createAllWindows;
    Scene_Map.prototype.createAllWindows = function() {
        _Scene_Map_createAllWindows.call(this);

        this._numberDisplay = new NumberDisplay(this);

        window.startNumberA = (from, to, totalFrame) => this._numberDisplay.startA(from, to, totalFrame);
        window.stopNumber = () => this._numberDisplay.stop();

        window.startNumberB = () => this._numberDisplay.startB();
        window.stopNumberB = () => this._numberDisplay.stopB();
    };

    //////////////////
    // update
    //////////////////
    const _Scene_Map_update_Number = Scene_Map.prototype.update;
    Scene_Map.prototype.update = function() {
        _Scene_Map_update_Number.call(this);
        if (this._numberDisplay) {
            this._numberDisplay.update();
        }
    };

})();