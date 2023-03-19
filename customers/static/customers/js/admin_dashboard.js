(function() {
  // Create set of all tasks
  let all_tasks = new Set();
  Object.entries(customer_tasks).forEach(([customer_name, tasks]) => {
    Object.keys(tasks).forEach(task_name => {
      all_tasks.add(task_name);
    });
  });

  console.log("All tasks: ", all_tasks);
})();
