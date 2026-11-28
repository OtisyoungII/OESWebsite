(() => {
  const menuButton = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('.site-nav');
  menuButton.addEventListener('click', () => {
    const open = menuButton.getAttribute('aria-expanded') !== 'true';
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Close menu' : 'Open menu');
    navigation.classList.toggle('open', open);
  });
  navigation.querySelectorAll('a').forEach(link => link.addEventListener('click', () => {
    navigation.classList.remove('open');
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open menu');
  }));

  const filters = document.querySelectorAll('.filter');
  const events = document.querySelectorAll('.event-row');
  const count = document.getElementById('event-count');
  filters.forEach(button => button.addEventListener('click', () => {
    filters.forEach(item => {
      const active = item === button;
      item.classList.toggle('active', active);
      item.setAttribute('aria-pressed', String(active));
    });
    let visible = 0;
    events.forEach(event => {
      event.hidden = button.dataset.filter !== 'all' && event.dataset.category !== button.dataset.filter;
      if (!event.hidden) visible++;
    });
    count.textContent = `Showing ${visible} sample event${visible === 1 ? '' : 's'}`;
  }));

  const dialog = document.getElementById('demo-dialog');
  const dialogContent = document.getElementById('dialog-content');
  document.getElementById('dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
  const parkDetails = {
    veterans: { title: 'Veterans Park', description: 'A central neighborhood park with playgrounds, courts, green space, and access to the historic stadium area. The official HPC site has the latest facility details.', link: 'https://hamtramckparks.com/hamtramck-locations/' },
    stadium: { title: 'Historic Hamtramck Stadium', description: 'A restored landmark celebrating Hamtramck’s baseball heritage and offering a memorable community setting. Check official sources for current access and programs.', link: 'https://hamtramckparks.com/hamtramck-locations/' },
    playfair: { title: 'Playfair & the district', description: 'The broader recreation district brings together fields and public spaces for sport and community activity. Facilities and access may change.', link: 'https://hamtramckparks.com/hamtramck-locations/' }
  };
  document.querySelectorAll('.park-detail').forEach(button => button.addEventListener('click', () => {
    const park = parkDetails[button.dataset.park];
    dialogContent.replaceChildren();
    const title = document.createElement('h2'); title.id = 'dialog-title'; title.textContent = park.title;
    const description = document.createElement('p'); description.textContent = park.description;
    const note = document.createElement('p'); note.textContent = 'This panel demonstrates a future park detail view. Details are illustrative.';
    const link = document.createElement('a'); link.className = 'button button-dark'; link.href = park.link; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = 'Check official park information ↗';
    dialogContent.append(title, description, note, link);
    dialog.showModal();
  }));
  document.querySelectorAll('.event-action').forEach(button => button.addEventListener('click', () => {
    dialogContent.replaceChildren();
    const title = document.createElement('h2'); title.id = 'dialog-title'; title.textContent = button.dataset.event;
    const description = document.createElement('p'); description.textContent = 'This is an illustrative event card demonstrating an event detail view. The date and activity are not scheduled. A production version could combine verified calendars and registration links.';
    const link = document.createElement('a'); link.className = 'button button-dark'; link.href = 'https://hamtramckparks.com/events/'; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.textContent = 'View official HPC events ↗';
    dialogContent.append(title, description, link);
    dialog.showModal();
  }));

  document.querySelector('[data-open="volunteer"]').addEventListener('click', () => {
    dialogContent.innerHTML = '<h2 id="dialog-title">Volunteer with your neighbors</h2><p>Try a sample volunteer interest flow. No name, email, phone number, waiver, or account is requested or stored.</p><label for="volunteer-activity">Choose an interest</label><select id="volunteer-activity"><option>Park beautification</option><option>Event support</option><option>Community gardening</option></select><label class="check-row"><input id="volunteer-training" type="checkbox"> I would review training and waiver information in a real registration.</label><button id="volunteer-preview" class="button button-dark" type="button">Preview next step →</button><p id="volunteer-result" role="status" aria-live="polite"></p>';
    document.getElementById('volunteer-preview').addEventListener('click', () => {
      const interest = document.getElementById('volunteer-activity').value;
      const reviewed = document.getElementById('volunteer-training').checked;
      document.getElementById('volunteer-result').textContent = reviewed ? `Demo complete: ${interest} selected. A real workflow would show verified opportunities and secure registration.` : 'Please check the training and waiver acknowledgment to preview the next step.';
    });
    dialog.showModal();
  });

  const dateInput = document.getElementById('rental-date');
  dateInput.min = new Date().toISOString().slice(0, 10);
  document.getElementById('rental-form').addEventListener('submit', event => {
    event.preventDefault();
    const result = document.getElementById('rental-result');
    const values = [document.getElementById('facility').value, dateInput.value, document.getElementById('rental-time').value, document.getElementById('rental-type').value];
    if (values.some(value => !value)) return;
    result.replaceChildren();
    const title = document.createElement('h3'); title.textContent = 'Sample inquiry ready';
    const summary = document.createElement('p'); summary.textContent = `${values[3]} at ${values[0]} on ${values[1]} (${values[2].toLowerCase()}). This is a local preview only; no availability was checked and no reservation was made.`;
    result.append(title, summary); result.hidden = false; result.focus();
  });

  let amount = '50';
  const givingMessage = document.getElementById('giving-message');
  document.querySelectorAll('[data-amount]').forEach(button => button.addEventListener('click', () => {
    amount = button.dataset.amount;
    document.querySelectorAll('[data-amount]').forEach(item => {
      const selected = item === button;
      item.classList.toggle('selected', selected);
      item.setAttribute('aria-pressed', String(selected));
    });
    givingMessage.textContent = `Your sample gift: $${amount}`;
  }));
  document.getElementById('give-button').addEventListener('click', () => {
    givingMessage.textContent = `A $${amount} sample gift could support stronger shared spaces. This demonstration has no checkout or payment processing.`;
  });
})();
