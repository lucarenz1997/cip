def log_execution(func):
    def wrapper(*args, **kwargs):
        print(f"Execution of {func.__name__} started")
        result = func(*args, **kwargs)
        print(f"Execution of {func.__name__} finished")
        return result

    return wrapper