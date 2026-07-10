export function requireTitle(input: { title?: string }): string {
  if (!input.title || input.title.trim() === "") {
    throw new Error("title is required");
  }

  return input.title.trim();
}
