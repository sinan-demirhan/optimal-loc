# Calculate the sum of values
def return_message(my_input: int):
    """

    Params:
    ----------
    my_input: int/float : constant

    Returns:
    -------
    The total of values

    Usage:
    -------
    from optimal_loc import return_message
    return_message(my_input=5)
    """
    my_data = [1, 2, 3, 4]
    return sum(my_data) * my_input
