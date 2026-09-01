/**
 * Utility to wrap async functions in a try-catch block. Useful for running async
 * functions in useEffect hooks.
 * @param {() => void} func - The async function to run
 * @param {((msg: unknown) => void) | string} onErrorMsg - Optional error message, or error function
 * @returns {Promise<void>}
 */
export async function handlePromiseRejection(
  func: () => void,
  onErrorMsg?: ((msg: unknown) => void) | string
): Promise<void> {
  try {
    await func();
  } catch (error) {
    if (onErrorMsg === undefined) {
      console.error(error);
    } else if (typeof onErrorMsg === "string") {
      console.error(`${onErrorMsg}: ${error}`);
    } else {
      onErrorMsg(error);
    }
  }
}

export const formatPatientInitials = (name: string) => {
  return name
    .split(" ")
    .map((n) => (n[0] ? n[0].toUpperCase() : ""))
    .join("");
};
