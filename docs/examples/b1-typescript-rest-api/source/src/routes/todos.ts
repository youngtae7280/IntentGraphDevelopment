import { addTodo, listTodos } from "../service/todoService";

export const todoRoutes = [
  {
    method: "GET",
    path: "/todos",
    handler: listTodos,
  },
  {
    method: "POST",
    path: "/todos",
    handler: addTodo,
  },
];
