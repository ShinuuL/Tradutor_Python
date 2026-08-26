//=============================================================================
// DrawCircle.js
//=============================================================================
/*:
 * @plugindesc 画面に円を表示するテスト
 * @author hami 
 * 
 * @help
 * Start startGauge(n); Example: startGauge(180);
 * Stop stopGauge();
 * 再開  continueGauge(n); 例 continueGauge(360);
 */

(function() {

    // Default animation required frames (changing this will affect the entire game)
    const DEFAULT_TOTAL_FRAME = 60;

    class CircleGauge {
        constructor(scene) {
            this._size = 120;

            // Add a drawing layer above the picture container
            this._layer = new Sprite();
            const pictureIndex = scene._spriteset.children.indexOf(scene._spriteset._pictureContainer);
            scene._spriteset.addChildAt(this._layer, pictureIndex + 1);

            // Publish to allow other plugins like DisplayNumber.js / Tgame.js to share the same layer
            scene._myLayer = this._layer;

            this._bitmap = new Bitmap(this._size, this._size);
            this._sprite = new Sprite(this._bitmap);
            this._sprite.x = 733;
            this._sprite.y = 492;
            this._sprite.visible = false;
            this._layer.addChild(this._sprite);

            this._numberBitmap = ImageManager.loadPicture('UI_number_1');

            this._frame = 0;
            this._playing = false;
            this._targetAngle = 360;
            this._currentAngle = 0;
            this._totalFrame = DEFAULT_TOTAL_FRAME;
        }

        start(angle, totalFrame) {
            this._currentAngle = 0;
            this._targetAngle = angle;
            this._totalFrame = totalFrame || DEFAULT_TOTAL_FRAME;
            this._frame = 0;
            this._playing = true;
            this._sprite.visible = true;
        }

        stop() {
            this._playing = false;
            this._sprite.visible = false;
            this._frame = 0;
        }

        continue(angle, totalFrame) {
            this._currentAngle = this._targetAngle;
            this._targetAngle = angle;
            this._totalFrame = totalFrame || DEFAULT_TOTAL_FRAME;
            this._frame = 0;
            this._playing = true;
            this._sprite.visible = true;
        }

        update() {
            if (!this._playing) return;

            if (this._frame >= this._totalFrame) {
                this._playing = false;
                return;
            }

            this._frame++;
            this._draw();
        }

        _draw() {
            const size = this._size;
            const ctx = this._bitmap._context;
            ctx.imageSmoothingEnabled = false;

            const rate = this._frame / this._totalFrame;
            const currentAngleRate = this._currentAngle / 360;
            const targetAngleRate = this._targetAngle / 360;
            const drawRate = Math.min(
                currentAngleRate + rate * (targetAngleRate - currentAngleRate),
                targetAngleRate
            );

            ctx.clearRect(0, 0, size, size);

            const dotSize = 3;
            const cx = size / 2;
            const cy = size / 2;
            const r = 51;
            const lw = 18;
            const innerR = r - lw / 2;
            const outerR = r + lw / 2;
            const startAngle = -Math.PI / 2;
            const endAngle = startAngle + Math.PI * 2 * drawRate;

            for (let y = -cy; y < cy; y += dotSize) {
                for (let x = -cx; x < cx; x += dotSize) {
                    const dist = Math.sqrt(
                        (x + dotSize / 2) * (x + dotSize / 2) +
                        (y + dotSize / 2) * (y + dotSize / 2)
                    );
                    const inRing = dist >= innerR && dist <= outerR;
                    const angle = Math.atan2(y + dotSize / 2, x + dotSize / 2);
                    const normalizedAngle = angle < startAngle ? angle + Math.PI * 2 : angle;
                    const inArc = normalizedAngle >= startAngle && normalizedAngle <= endAngle;
                    const px = x + cx;
                    const py = y + cy;

                    ctx.clearRect(px, py, dotSize, dotSize);
                    if (inRing && inArc) {
                        ctx.fillStyle = '#fcadc5';
                        ctx.fillRect(px, py, dotSize, dotSize);
                    }
                }
            }

            this._drawPercentText(drawRate, cx, cy);
            this._bitmap._setDirty();
        }

        _drawPercentText(drawRate, cx, cy) {
            const percent = Math.round(drawRate * 100);
            const str = percent + '%';
            const charWidth = 18;
            const charHeight = 27;
            const startX = cx - (str.length * charWidth) / 2;

            for (let i = 0; i < str.length; i++) {
                const ch = str[i];
                const srcX = ch === '%' ? 10 * charWidth : parseInt(ch) * charWidth;

                this._bitmap.blt(
                    this._numberBitmap,
                    srcX, 0,
                    charWidth, charHeight,
                    startX + i * charWidth,
                    cy - charHeight / 2
                );
            }
        }
    }

    const _Scene_Map_createAllWindows = Scene_Map.prototype.createAllWindows;
    Scene_Map.prototype.createAllWindows = function() {
        _Scene_Map_createAllWindows.call(this);

        this._circleGauge = new CircleGauge(this);

        // Prepare global functions as usual to be called from external sources like event script commands
        window.startGauge = (angle, totalFrame) => this._circleGauge.start(angle, totalFrame);
        window.stopGauge = () => this._circleGauge.stop();
        window.continueGauge = (angle, totalFrame) => this._circleGauge.continue(angle, totalFrame);
    };

    const _Scene_Map_update_Circle = Scene_Map.prototype.update;
    Scene_Map.prototype.update = function() {
        _Scene_Map_update_Circle.call(this);
        if (this._circleGauge) {
            this._circleGauge.update();
        }
    };

})();