/**
 * Pixel work that would otherwise sit on the main thread: shrinking decoded textures, and reading a decoded texture back out as
 * bytes, a stripe at a time, for uploading. The messages are { id, op, ... } and every answer carries the same id. Bitmaps are
 * transferred, not cloned (cloning one costs the main thread tens of ms), and always come back or are replaced.
 */
const open = new Map(); // id -> { bitmap, canvas, cx }

self.onmessage = async ({ data }) => {
  const { id, op } = data;
  try {
    if (op === 'ping') {
      self.postMessage({ id });
    } else if (op === 'shrink') {
      let small;
      try {
        small = await createImageBitmap(data.bitmap, { resizeWidth: data.width, resizeHeight: data.height, resizeQuality: 'high' });
      } catch (error) {
        // Hand the original back: it was transferred here and would otherwise be lost.
        self.postMessage({ id, error: String(error), bitmap: data.bitmap }, [data.bitmap]);
        return;
      }
      data.bitmap.close();
      self.postMessage({ id, bitmap: small }, [small]);
    } else if (op === 'open') {
      const canvas = new OffscreenCanvas(data.bitmap.width, data.rows);
      const cx = canvas.getContext('2d', { willReadFrequently: true });
      cx.globalCompositeOperation = 'copy';
      open.set(id, { bitmap: data.bitmap, cx });
      self.postMessage({ id });
    } else if (op === 'stripe') {
      const { bitmap, cx } = open.get(id);
      cx.drawImage(bitmap, 0, data.y, bitmap.width, data.height, 0, 0, bitmap.width, data.height);
      const px = cx.getImageData(0, 0, bitmap.width, data.height).data;
      const words = new Uint32Array(px.buffer, px.byteOffset, px.length >> 2);
      let opaque = true;
      for (let i = 0; i < words.length; i++) {
        if (words[i] >>> 24 !== 255) {
          opaque = false;
          break;
        }
      }
      if (opaque) {
        self.postMessage({ id, px, opaque }, [px.buffer]);
      } else {
        // A canvas keeps translucent pixels premultiplied, so the bytes would not be the texture's: send the exact crop instead.
        const stripe = await createImageBitmap(bitmap, 0, data.y, bitmap.width, data.height, { premultiplyAlpha: 'none', colorSpaceConversion: 'none' });
        self.postMessage({ id, stripe, opaque }, [stripe]);
      }
    } else if (op === 'close') {
      // The bitmap goes back to where it came from, whole.
      const held = open.get(id);
      open.delete(id);
      if (held) self.postMessage({ id, bitmap: held.bitmap }, [held.bitmap]);
      else self.postMessage({ id });
    }
  } catch (error) {
    self.postMessage({ id, error: String(error) });
  }
};
