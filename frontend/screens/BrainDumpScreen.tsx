import React, { useState, useCallback } from 'react';
import {
  ActivityIndicator,
  Alert,
  FlatList,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  RefreshControl,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';

import BrainDumpCard from '../components/braindump/BrainDumpCard';
import DumpDetailSheet from '../components/braindump/DumpDetailSheet';
import EditDumpSheet from '../components/braindump/EditDumpSheet';
import ElvynMascot from '../components/ElvynMascot';
import VoiceCaptureButton from '../components/VoiceCaptureButton';
import { createBrainDump, deleteBrainDump, getRecentDumps } from '../services/braindump';
import { useColors } from '../theme/colors';
import { BrainDump } from '../types/brainDump';

const SAVE_ERROR = "Couldn't save that. Check your connection and try again.";
const LOAD_ERROR = "Couldn't load your dumps. Pull down to try again.";

export default function BrainDumpScreen() {
  const colors = useColors();
  const { width, fontScale } = useWindowDimensions();
  const scale = Math.min(1.1, Math.max(0.9, width / 390));
  const gutter = Math.round(20 * scale);
  const mascotSize = Math.min(104, Math.max(72, Math.round(width * 0.28)));
  const showCaptureMascot = width >= 340 && fontScale <= 1.3;
  const minInputHeight = Math.round(82 * scale);
  const maxInputHeight = Math.round(180 * scale);

  const [content, setContent] = useState('');
  const [source, setSource] = useState<'text' | 'voice'>('text');
  const [inputHeight, setInputHeight] = useState(minInputHeight);
  const [inputFocused, setInputFocused] = useState(false);
  const [dumps, setDumps] = useState<BrainDump[]>([]);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [loadingDumps, setLoadingDumps] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [saveFailed, setSaveFailed] = useState(false);

  const [activeDump, setActiveDump] = useState<BrainDump | null>(null);
  const [sheetVisible, setSheetVisible] = useState(false);
  const [menuDump, setMenuDump] = useState<BrainDump | null>(null);
  const [editingDump, setEditingDump] = useState<BrainDump | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadDumps = useCallback(async () => {
    setLoadingDumps(true);
    setLoadFailed(false);
    try {
      setDumps(await getRecentDumps());
    } catch (error) {
      console.warn('Failed to load brain dumps:', error);
      setLoadFailed(true);
    } finally {
      setLoadingDumps(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      void loadDumps();
    }, [loadDumps]),
  );

  const handleSave = async () => {
    if (!content.trim() || saving) return;
    setSaving(true);
    setSaveFailed(false);
    try {
      await createBrainDump(content.trim(), source);
      setContent('');
      setSource('text');
      setInputHeight(minInputHeight);
      await loadDumps();
    } catch (error) {
      console.warn('Failed to save brain dump:', error);
      setSaveFailed(true);
    } finally {
      setSaving(false);
    }
  };

  const handleVoiceTranscript = (text: string) => {
    setContent(text.slice(0, 1000));
    setSource('voice');
    setSaveFailed(false);
  };

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await loadDumps();
    } finally {
      setRefreshing(false);
    }
  };

  const handleDelete = async (dump: BrainDump) => {
    setDeleting(true);
    try {
      await deleteBrainDump(dump.id);
      setDumps((current) => current.filter((item) => item.id !== dump.id));
      setMenuDump(null);
      if (activeDump?.id === dump.id) {
        setSheetVisible(false);
        setActiveDump(null);
      }
    } catch (error) {
      console.warn('Failed to delete brain dump:', error);
      const message = "Couldn't delete that dump. Please try again.";
      if (Platform.OS === 'web') {
        window.alert(message);
      } else {
        Alert.alert('Could not delete brain dump', message);
      }
    } finally {
      setDeleting(false);
    }
  };

  const confirmDelete = (dump: BrainDump) => {
    setMenuDump(null);
    const confirmation = 'This will also remove it from AI memory.';
    if (Platform.OS === 'web') {
      if (window.confirm(`Delete this brain dump? ${confirmation}`)) void handleDelete(dump);
      return;
    }

    Alert.alert('Delete brain dump?', confirmation, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: () => void handleDelete(dump) },
    ]);
  };

  const listHeader = (
    <View>
      <View style={{ paddingHorizontal: gutter, paddingTop: 10, paddingBottom: 14 }}>
        <Text
          accessibilityRole="header"
          maxFontSizeMultiplier={1.2}
          style={{ color: colors.text, fontSize: 22, lineHeight: 28, fontWeight: '700' }}
        >
          Brain Dump
        </Text>
        <Text
          maxFontSizeMultiplier={1.4}
          style={{ color: colors.textMuted, fontSize: 13, lineHeight: 18, marginTop: 2 }}
        >
          Get it out. Sort it later.
        </Text>
      </View>

      <View style={{ paddingHorizontal: gutter }}>
        <View
          style={{
            backgroundColor: colors.surface,
            borderRadius: 20,
            padding: 16,
            marginBottom: 12,
            borderWidth: 1,
            borderColor: inputFocused ? colors.primary : colors.border,
          }}
        >
          <View style={{ flexDirection: 'row', alignItems: 'flex-start' }}>
            <View style={{ flex: 1, minWidth: 0, paddingRight: showCaptureMascot ? 8 : 0 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                <Ionicons name="sparkles-outline" size={18} color={colors.primary} />
                <Text
                  maxFontSizeMultiplier={1.2}
                  style={{
                    color: colors.text,
                    fontSize: 16,
                    lineHeight: 22,
                    fontWeight: '600',
                    marginLeft: 8,
                    flexShrink: 1,
                  }}
                >
                  What&apos;s on your mind?
                </Text>
              </View>
              <TextInput
                value={content}
                onChangeText={(text) => {
                  setContent(text);
                  setSaveFailed(false);
                  if (source === 'voice') setSource('text');
                }}
                onContentSizeChange={(event) => {
                  setInputHeight(
                    Math.min(
                      maxInputHeight,
                      Math.max(minInputHeight, Math.ceil(event.nativeEvent.contentSize.height)),
                    ),
                  );
                }}
                onFocus={() => setInputFocused(true)}
                onBlur={() => setInputFocused(false)}
                placeholder="Type anything: a thought, task, idea, worry or just something random. No need to organize it yet."
                placeholderTextColor={colors.textMuted}
                multiline
                maxLength={1000}
                maxFontSizeMultiplier={1.4}
                scrollEnabled={inputHeight >= maxInputHeight}
                textAlignVertical="top"
                accessibilityLabel="Brain dump text"
                style={{
                  minHeight: minInputHeight,
                  height: inputHeight,
                  color: colors.text,
                  fontSize: 14,
                  lineHeight: 20,
                  padding: 0,
                  margin: 0,
                }}
              />
            </View>
            {showCaptureMascot ? (
              <View style={{ width: mascotSize, alignItems: 'center', paddingTop: 22 }}>
                <ElvynMascot variant="supportive" size={mascotSize} />
              </View>
            ) : null}
          </View>

          <View
            style={{
              flexDirection: 'row',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderTopWidth: 1,
              borderTopColor: colors.border,
              marginTop: 12,
              paddingTop: 10,
            }}
          >
            <VoiceCaptureButton onTranscript={handleVoiceTranscript} />
            <Text
              maxFontSizeMultiplier={1.2}
              style={{
                color: content.length >= 950 ? colors.danger : colors.textMuted,
                fontSize: 12,
                lineHeight: 16,
                marginLeft: 8,
              }}
            >
              {content.length}/1000
            </Text>
          </View>
        </View>

        <TouchableOpacity
          onPress={() => void handleSave()}
          disabled={saving || !content.trim()}
          accessibilityRole="button"
          accessibilityLabel="Save brain dump"
          style={{
            minHeight: 52,
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: colors.primary,
            borderRadius: 14,
            marginBottom: 10,
            opacity: saving || !content.trim() ? 0.5 : 1,
          }}
        >
          {saving ? (
            <ActivityIndicator color={colors.surface} />
          ) : (
            <>
              <Ionicons name="save-outline" size={19} color={colors.surface} />
              <Text
                maxFontSizeMultiplier={1.2}
                style={{ color: colors.surface, fontSize: 16, lineHeight: 22, fontWeight: '600', marginLeft: 8 }}
              >
                Save
              </Text>
            </>
          )}
        </TouchableOpacity>

        {saveFailed ? (
          <Text
            accessibilityRole="alert"
            maxFontSizeMultiplier={1.4}
            style={{ color: colors.danger, fontSize: 13, lineHeight: 18, marginBottom: 10 }}
          >
            {SAVE_ERROR}
          </Text>
        ) : null}

        <View
          style={{
            flexDirection: 'row',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: 8,
            marginBottom: 10,
          }}
        >
          <Text
            accessibilityRole="header"
            maxFontSizeMultiplier={1.2}
            style={{ color: colors.text, fontSize: 16, lineHeight: 22, fontWeight: '600' }}
          >
            Recent dumps
          </Text>
          <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 12, lineHeight: 16 }}>
            {dumps.length}
          </Text>
        </View>
      </View>
    </View>
  );

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.background }} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <FlatList
          data={dumps}
          keyExtractor={(item) => item.id}
          ListHeaderComponent={listHeader}
          contentContainerStyle={{ paddingBottom: 16 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={() => void onRefresh()}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          renderItem={({ item }) => (
            <View style={{ paddingHorizontal: gutter }}>
              <BrainDumpCard
                dump={item}
                onMorePress={() => setMenuDump(item)}
                onPress={() => {
                  setActiveDump(item);
                  setSheetVisible(true);
                }}
              />
            </View>
          )}
          ListEmptyComponent={
            <View style={{ alignItems: 'center', paddingHorizontal: gutter, paddingTop: 22, paddingBottom: 28 }}>
              {loadingDumps ? (
                <ActivityIndicator color={colors.primary} />
              ) : loadFailed ? (
                <Text
                  accessibilityRole="alert"
                  maxFontSizeMultiplier={1.4}
                  style={{ color: colors.textMuted, fontSize: 14, lineHeight: 20, textAlign: 'center' }}
                >
                  {LOAD_ERROR}
                </Text>
              ) : (
                <>
                  <ElvynMascot variant="supportive" size={84} />
                  <Text
                    maxFontSizeMultiplier={1.4}
                    style={{
                      color: colors.textMuted,
                      fontSize: 14,
                      lineHeight: 20,
                      textAlign: 'center',
                      marginTop: 12,
                    }}
                  >
                    Nothing here yet. Whatever is on your mind can go here.
                  </Text>
                </>
              )}
            </View>
          }
        />
      </KeyboardAvoidingView>

      <DumpDetailSheet
        visible={sheetVisible}
        dump={activeDump}
        onClose={() => setSheetVisible(false)}
        onConverted={loadDumps}
      />

      <Modal
        visible={menuDump !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setMenuDump(null)}
      >
        <Pressable
          onPress={() => setMenuDump(null)}
          accessibilityRole="button"
          accessibilityLabel="Close brain dump options"
          style={{
            flex: 1,
            justifyContent: 'center',
            paddingHorizontal: 32,
            backgroundColor: colors.overlay,
          }}
        >
          <Pressable
            onPress={(event) => event.stopPropagation()}
            style={{
              backgroundColor: colors.surface,
              borderColor: colors.border,
              borderWidth: 1,
              borderRadius: 16,
              padding: 8,
            }}
          >
            <Text
              maxFontSizeMultiplier={1.2}
              style={{ paddingHorizontal: 12, paddingTop: 10, paddingBottom: 6, color: colors.textMuted, fontSize: 13 }}
            >
              Brain dump options
            </Text>
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Edit brain dump"
              onPress={() => {
                setEditingDump(menuDump);
                setMenuDump(null);
              }}
              style={{ minHeight: 44, justifyContent: 'center', paddingHorizontal: 14 }}
            >
              <Text maxFontSizeMultiplier={1.2} style={{ color: colors.text, fontSize: 16, lineHeight: 22 }}>
                Edit
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Delete brain dump"
              disabled={deleting}
              onPress={() => menuDump && confirmDelete(menuDump)}
              style={{ minHeight: 44, justifyContent: 'center', paddingHorizontal: 14 }}
            >
              <Text maxFontSizeMultiplier={1.2} style={{ color: colors.danger, fontSize: 16, lineHeight: 22 }}>
                {deleting ? 'Deleting…' : 'Delete'}
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              accessibilityRole="button"
              accessibilityLabel="Cancel"
              onPress={() => setMenuDump(null)}
              style={{ minHeight: 44, justifyContent: 'center', paddingHorizontal: 14 }}
            >
              <Text maxFontSizeMultiplier={1.2} style={{ color: colors.textMuted, fontSize: 16, lineHeight: 22 }}>
                Cancel
              </Text>
            </TouchableOpacity>
          </Pressable>
        </Pressable>
      </Modal>

      {editingDump ? (
        <EditDumpSheet
          visible
          dump={editingDump}
          onClose={() => setEditingDump(null)}
          onSaved={(updated) => {
            setDumps((current) => current.map((item) => (item.id === updated.id ? updated : item)));
            if (activeDump?.id === updated.id) setActiveDump(updated);
            setEditingDump(null);
          }}
        />
      ) : null}
    </SafeAreaView>
  );
}
