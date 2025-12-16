import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_excel('incidents_nucli_UCIH_2025.xlsx')
print(df.info())

import pandas as pd
import matplotlib.pyplot as plt

def plot_pie_from_column(df, column_name):
    """
    Generates a pie chart for the count and percentage of each category
    in the specified column of a DataFrame.

    Args:
        df (pd.DataFrame): The input DataFrame.
        column_name (str): The name of the column to plot.

    Returns:
        str: The filename of the saved pie chart image.
    """
    # Calculate counts
    counts = df[column_name].value_counts()
    total_count = counts.sum()

    if total_count == 0:
        print(f"Column '{column_name}' has no data to plot.")
        return None

    # Define the custom autopct function to show both percentage and count
    def make_autopct(values):
        def my_autopct(pct):
            # Calculate the count for the current slice
            count = int(round(pct * total_count / 100.0))
            return f'{pct:.1f}%\n({count})'
        return my_autopct

    # Create the plot
    plt.figure(figsize=(10, 8))
    plt.pie(
        counts,
        labels=counts.index,
        autopct=make_autopct(counts),
        startangle=90,
        textprops={'fontsize': 12},
        wedgeprops={'edgecolor': 'black'}
    )

    # Set title
    plt.title(f'Distribució de {column_name}', fontsize=12, fontweight='bold', loc='left')

    # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.axis('equal')

    # Save the figure
    # Replace spaces in column name with underscores for a valid filename
    output_filename = f'{column_name.replace(" ", "_")}_pie_chart.png'
    plt.savefig(output_filename)
    plt.close()

    print(f"Pie chart saved as {output_filename}")
    return output_filename

plot_pie_from_column(df, 'Risc')
plot_pie_from_column(df, 'Categ. prof. notificant')