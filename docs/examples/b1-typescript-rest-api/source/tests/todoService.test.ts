import { addTodo, listTodos } from "../src/service/todoService";

export function testAddTodoCreatesOpenTodo(): void {
  const todo = addTodo({ title: "Write IntentGraph tests" });
  if (todo.completed !== false) {
    throw new Error("new todo should be incomplete");
  }
}

export function testListTodosStartsEmpty(): void {
  const todos = listTodos();
  if (todos.length !== 0) {
    throw new Error("todo list should start empty");
  }
}
