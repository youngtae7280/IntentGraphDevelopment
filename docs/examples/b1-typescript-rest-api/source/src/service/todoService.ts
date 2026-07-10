import { createTodo, type Todo } from "../model/todo";
import { requireTitle } from "../validation/input";

export function addTodo(input: { title?: string }): Todo {
  const title = requireTitle(input);
  return createTodo("todo-1", title);
}

export function listTodos(): Todo[] {
  return [];
}
