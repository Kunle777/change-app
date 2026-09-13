import { Modal, View, Text, TouchableOpacity, Pressable } from 'react-native';

interface TaskActionsSheetProps {
  visible: boolean;
  onClose: () => void;
  onMarkDone: () => void;
  onNotNow: () => void;
  onReschedule: () => void;
  onEdit: () => void;
  onCancel: () => void;
}

export default function TaskActionsSheet({
  visible,
  onClose,
  onMarkDone,
  onNotNow,
  onReschedule,
  onEdit,
  onCancel,
}: TaskActionsSheetProps) {
  const actions = [
    { label: 'Mark as done', onPress: onMarkDone },
    { label: 'Not now', onPress: onNotNow },
    { label: 'Reschedule', onPress: onReschedule },
    { label: 'Edit task', onPress: onEdit },
    { label: 'Cancel task', onPress: onCancel, destructive: true },
  ];

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable style={{ flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' }} onPress={onClose}>
        <View
          style={{
            marginTop: 'auto',
            backgroundColor: '#fff',
            borderTopLeftRadius: 20,
            borderTopRightRadius: 20,
            paddingVertical: 8,
            paddingBottom: 24,
          }}
        >
          <Text style={{ textAlign: 'center', fontWeight: '600', padding: 14 }}>Task actions</Text>
          {actions.map((a) => (
            <TouchableOpacity
              key={a.label}
              onPress={() => {
                onClose();
                a.onPress();
              }}
              style={{
                paddingVertical: 14,
                paddingHorizontal: 20,
                borderTopWidth: 1,
                borderTopColor: '#F1F1F5',
              }}
            >
              <Text
                style={{
                  fontSize: 15,
                  color: a.destructive ? '#EF4444' : '#111',
                  textAlign: 'center',
                }}
              >
                {a.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </Pressable>
    </Modal>
  );
}
