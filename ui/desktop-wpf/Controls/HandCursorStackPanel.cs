using Microsoft.UI.Input;
using Microsoft.UI.Xaml.Controls;

namespace LibreOfficeAI.Controls
{
    public class HandCursorStackPanel : StackPanel
    {
        public HandCursorStackPanel()
        {
            this.PointerEntered += (_, __) =>
            {
                this.ProtectedCursor = InputSystemCursor.Create(InputSystemCursorShape.Hand);
            };

            this.PointerExited += (_, __) =>
            {
                this.ProtectedCursor = InputSystemCursor.Create(InputSystemCursorShape.Arrow);
            };
        }
    }
}
