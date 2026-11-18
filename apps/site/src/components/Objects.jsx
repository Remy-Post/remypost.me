import { useSyncExternalStore } from 'react';
import { getStatus, isReady, objectsOn, onObjects, onReady, onStatus, setObjects } from '../three/live.js';

/** Are the 3D objects switched on? Re-renders when the visitor flips the switch. (It does not say they are there: see useLive.) */
export const useObjects = () => useSyncExternalStore(onObjects, objectsOn);

/** The stage's real state: 'off', 'loading', 'live' or 'unavailable' (no usable WebGL, or the stage failed to start). */
export const useStatus = () => useSyncExternalStore(onStatus, getStatus);

/**
 * Is this object (a project's `object` name, or 'education', 'experience', 'links') really on the stage, loaded and
 * drawable? Text that promises something to do with it (a hint, a label, a tab stop) follows this, not the switch.
 */
export const useLive = (name) => useSyncExternalStore(onReady, () => !!name && isReady(name));

/**
 * The 3D switch in the bar: a real `role="switch"` (label "3D", `aria-checked` the state), a small track and thumb, a 44 px target. The
 * choice is kept (see setObjects). Where the browser cannot show the 3D it says so and does nothing.
 */
export function ObjectsSwitch() {
  const on = useObjects();
  const status = useStatus();
  const unavailable = on && status === 'unavailable';
  return (
    <button
      type="button"
      role="switch"
      className="switch"
      aria-checked={on && !unavailable}
      aria-disabled={unavailable ? 'true' : undefined}
      onClick={unavailable ? undefined : () => setObjects(!on)}
      title={unavailable ? 'This browser cannot show the 3D objects, so the pictures are shown instead' : on ? 'Turn the 3D objects off' : 'Turn the 3D objects on'}
    >
      <span className="switch__label">{unavailable ? '3D unavailable' : '3D'}</span>
      <span className="switch__track" aria-hidden="true">
        <span className="switch__thumb" />
      </span>
    </button>
  );
}
