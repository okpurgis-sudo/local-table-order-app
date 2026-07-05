function yen(value) {
  return Number(value || 0).toLocaleString("ja-JP") + "円";
}

function updateCartLink(cartLink, count, totalText) {
  if (!cartLink) return;
  cartLink.textContent = count > 0
    ? "カートを見る（" + count + "点 / " + totalText + "）"
    : "カートを見る";
}

document.querySelectorAll("[data-quantity-form]").forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const submitter = event.submitter;
    const card = form.closest("[data-product-card]");
    const quantityText = card.querySelector("[data-quantity-text]");
    const subtotalText = card.querySelector("[data-subtotal-text]");
    const plusButton = card.querySelector("[data-plus-button]");
    const minusButton = card.querySelector("[data-minus-button]");
    const cartLink = document.querySelector("[data-cart-link]");
    const price = Number(card.dataset.price || 0);

    const formData = new FormData(form);
    formData.set("delta", submitter.value);

    plusButton.disabled = true;
    minusButton.disabled = true;

    try {
      const response = await fetch(form.action, {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });

      const data = await response.json();
      if (!response.ok || !data.ok) {
        alert(data.message || "数量を変更できませんでした。");
        return;
      }

      const quantity = Number(data.quantity || 0);
      const maxQuantity = Number(data.max_quantity || card.dataset.maxQuantity || 5);

      quantityText.textContent = quantity;
      subtotalText.textContent = quantity > 0
        ? "選択中：" + quantity + "点 / " + yen(price * quantity)
        : "未選択";

      minusButton.disabled = quantity <= 0;
      plusButton.disabled = quantity >= maxQuantity;
      updateCartLink(cartLink, Number(data.cart_count || 0), data.cart_total_text || yen(data.cart_total));

      card.classList.add("quantity-changed");
      setTimeout(() => card.classList.remove("quantity-changed"), 350);
    } catch (error) {
      alert("通信に失敗しました。もう一度お試しください。");
    } finally {
      if (quantityText) {
        const current = Number(quantityText.textContent || 0);
        const maxQuantity = Number(card.dataset.maxQuantity || 5);
        minusButton.disabled = current <= 0;
        plusButton.disabled = current >= maxQuantity;
      }
    }
  });
});
