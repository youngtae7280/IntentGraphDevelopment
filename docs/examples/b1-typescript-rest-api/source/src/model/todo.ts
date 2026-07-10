export interface Todo {
  id: string;
  title: string;
  completed: boolean;
}

export function createTodo(id: string, title: string): Todo {
  return {
    id,
    title,
    completed: false,
  };
}
