# RunFunctionProgressBar

RunFunctionProgressBar is a Python application for tracking the progress of heavy functions and handling errors during their execution. It provides a graphical user interface (GUI) to monitor the progress of long-running functions and handles errors gracefully.

## Getting Started

To get started with RunFunctionProgressBar, follow these steps:

1. **Prerequisites**: Make sure you have Python and the required libraries installed. You can install the dependencies using pip:

   ```bash
   pip install qtpy
   ```

2. **Clone the Repository**: Clone this repository to your local machine:

   ```bash
   git clone https://github.com/Sorantan/RunFunctionProgressBar.git
   ```

3. **Run the Application**: Navigate to the project directory and run the main script:

   ```bash
   python progress_bar.py
   ```

   This will open the main application window.

## Features

- Run heavy functions in the background while displaying a progress bar.
- Handle errors gracefully, allowing you to view and diagnose exceptions.
- Track and predict execution times for functions.
- Simple and user-friendly graphical user interface.

## Usage

1. Launch the application.
2. Click one of the "Start" buttons to run a sample heavy function.
3. A new progress bar window will appear, displaying the progress of the function.
4. Observe the progress, and if an error occurs, the application will display the error details.
5. Once the function completes, the progress bar window will close automatically.

## Customization

You can customize the application by modifying the `heavy_function` and `error_function` functions or by adding your own functions. You can also adjust the initial end time for function execution.

<!-- ## Contributing

If you want to contribute to this project or report issues, please follow the [GitHub guidelines for contributing](CONTRIBUTING.md). -->

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This project uses the QtPy library for GUI components.
- Special thanks to the developers and contributors of QtPy and PyQt.

Enjoy using RunFunctionProgressBar!
