// The command palette: Quasar's searchable select, empty until a word is typed. An option shows when
// each typed word is in its title or keywords; one that cannot run is shown disabled, with its reason.
export default {
  props: ["options", "text"],
  emits: ["choose"],
  template: `
    <q-select
      ref="qRef"
      :model-value="null"
      :options="shown"
      option-value="id"
      option-label="title"
      option-disable="disable"
      use-input
      hide-dropdown-icon
      input-debounce="0"
      outlined
      dense
      autofocus
      label="Type a command"
      data-control="palette-input"
      @filter="filter"
      @update:model-value="choose"
    >
      <template v-slot:option="scope">
        <q-item v-bind="scope.itemProps" data-control="palette-item">
          <q-item-section>
            <q-item-label>{{ scope.opt.title }}</q-item-label>
            <q-item-label v-if="scope.opt.disable" caption>{{ scope.opt.reason }}</q-item-label>
          </q-item-section>
          <q-item-section v-if="scope.opt.chord" side>{{ scope.opt.chord }}</q-item-section>
        </q-item>
      </template>
      <template v-slot:no-option>
        <q-item data-control="palette-none">
          <q-item-section>No command matches</q-item-section>
        </q-item>
      </template>
    </q-select>
  `,
  data() {
    return { shown: [] };
  },
  methods: {
    type() {
      // Called once the dialog has opened: text in the address (?palette=<text>) is typed as if
      // by the user, which needs the input focused.
      const select = this.$refs.qRef;
      select.focus();
      if (this.text) {
        select.updateInputValue(this.text, true);
        select.showPopup();
      }
    },
    filter(text, update, abort) {
      const words = text.toLocaleLowerCase().split(/\s+/).filter(Boolean);
      // No word lists nothing: the palette is a search, not a menu.
      if (words.length === 0) {
        abort();
        return;
      }
      update(
        () => {
          this.shown = this.options.filter((o) => words.every((w) => o.words.includes(w)));
        },
        (select) => {
          // Enter runs the first command that can run.
          if (this.shown.length > 0) {
            select.setOptionIndex(-1);
            select.moveOptionSelection(1, true);
          }
        },
      );
    },
    choose(option) {
      if (option && !option.disable) this.$emit("choose", option.id);
    },
  },
};
